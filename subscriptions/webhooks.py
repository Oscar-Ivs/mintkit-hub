# subscriptions/webhooks.py
import datetime
import logging
from urllib.parse import urlsplit

import stripe
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan
from .stripe_service import init_stripe

logger = logging.getLogger(__name__)


# -------------------------
# Helpers
# -------------------------
def _utc_from_ts(ts):
    # Stripe timestamps are unix seconds; convert to timezone-aware UTC datetime
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


def _profile_email(profile: Profile) -> str:
    # Profile email preferred, fallback to user email
    return (getattr(profile, "contact_email", "") or "").strip() or (profile.user.email or "").strip()


def _site_parts():
    """
    Build protocol/domain/site_root from SITE_URL.
    Keeps email templates consistent with welcome/reset style.
    """
    raw_site = (settings.SITE_URL or "").rstrip("/")
    parts = urlsplit(raw_site)

    if parts.scheme and parts.netloc:
        protocol = parts.scheme
        domain = parts.netloc
        site_root = f"{protocol}://{domain}"
        return protocol, domain, site_root

    # Fallback if SITE_URL was set without scheme
    domain = raw_site.replace("https://", "").replace("http://", "").split("/")[0]
    protocol = "https"
    site_root = f"{protocol}://{domain}"
    return protocol, domain, site_root


def _base_email_ctx(profile: Profile, plan_name: str):
    protocol, domain, site_root = _site_parts()

    return {
        "first_name": profile.user.first_name or profile.user.username,
        "plan_name": plan_name,
        # base_email.html expects these
        "protocol": protocol,
        "domain": domain,
        "site_root": site_root,
        # Common links used in templates
        "dashboard_url": f"{site_root}/accounts/dashboard/",
        "portal_url": f"{site_root}/subscriptions/portal/",
        "about_url": f"{site_root}/about/",
        "pricing_url": f"{site_root}/pricing/",
        "faq_url": f"{site_root}/faq/",
        # Footer/support
        "support_email": "support@mintkit.co.uk",
    }


def _send_email(template_html, template_txt, subject, to_email, ctx):
    html_body = render_to_string(template_html, ctx)
    txt_body = render_to_string(template_txt, ctx)

    msg = EmailMultiAlternatives(subject=subject, body=txt_body, to=[to_email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


def _find_local_subscription_by_stripe_id(stripe_sub_id: str):
    return (
        Subscription.objects.select_related("profile", "plan")
        .filter(stripe_subscription_id=stripe_sub_id)
        .first()
    )


def _find_profile_for_subscription(stripe_sub):
    """
    Prefer subscription metadata (set at Checkout creation).
    Fallback to local DB via stripe_subscription_id.
    """
    md = stripe_sub.get("metadata") or {}
    profile_id = md.get("profile_id")

    if profile_id:
        try:
            return Profile.objects.get(pk=profile_id)
        except Profile.DoesNotExist:
            return None

    sub_id = stripe_sub.get("id")
    local = _find_local_subscription_by_stripe_id(sub_id) if sub_id else None
    return local.profile if local else None


def _resolve_plan(stripe_sub, existing_sub: Subscription | None):
    """
    Resolve plan reliably:
    1) existing local subscription plan (best for portal events)
    2) metadata plan_code (checkout flow)
    3) price-id match (fallback)
    """
    if existing_sub and existing_sub.plan:
        return existing_sub.plan

    md = stripe_sub.get("metadata") or {}
    plan_code = (md.get("plan_code") or "").strip().lower()
    if plan_code:
        plan = SubscriptionPlan.objects.filter(code=plan_code).first()
        if plan:
            return plan

    # Fallback: try price id from subscription items
    price_id = None
    items = stripe_sub.get("items") or {}
    data = items.get("data") if isinstance(items, dict) else None
    if isinstance(data, list) and data:
        item0 = data[0] or {}
        price = item0.get("price")
        if isinstance(price, dict):
            price_id = price.get("id")
        elif isinstance(price, str):
            price_id = price

    # If not present in payload, retrieve full sub once
    if not price_id and stripe_sub.get("id"):
        try:
            full = stripe.Subscription.retrieve(stripe_sub["id"], expand=["items.data.price"])
            items = full.get("items") or {}
            data = items.get("data") if isinstance(items, dict) else None
            if isinstance(data, list) and data:
                price = (data[0] or {}).get("price") or {}
                if isinstance(price, dict):
                    price_id = price.get("id")
        except Exception:
            logger.exception("Plan resolve: failed retrieving subscription for price id")

    # Map known price ids -> plan code
    price_map = {
        (getattr(settings, "STRIPE_PRICE_BASIC", "") or "").strip(): "basic",
        (getattr(settings, "STRIPE_PRICE_BASIC_ANNUAL", "") or "").strip(): "basic",
        (getattr(settings, "STRIPE_PRICE_PRO", "") or "").strip(): "pro",
        (getattr(settings, "STRIPE_PRICE_PRO_ANNUAL", "") or "").strip(): "pro",
    }
    plan_code = price_map.get((price_id or "").strip())
    if plan_code:
        plan = SubscriptionPlan.objects.filter(code=plan_code).first()
        if plan:
            return plan

    return None


def _map_status(stripe_status: str):
    status_map = {
        "active": Subscription.STATUS_ACTIVE,
        "trialing": Subscription.STATUS_TRIALING,
        "past_due": Subscription.STATUS_PAST_DUE,
        "unpaid": Subscription.STATUS_PAST_DUE,
        "incomplete": Subscription.STATUS_INCOMPLETE,
        "incomplete_expired": Subscription.STATUS_INCOMPLETE,
        "canceled": Subscription.STATUS_CANCELED,
        "cancelled": Subscription.STATUS_CANCELED,
    }
    return status_map.get((stripe_status or "").strip().lower(), Subscription.STATUS_CANCELED)


# -------------------------
# Webhook
# -------------------------
@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook endpoint.
    Ensure Stripe webhook endpoint includes:
    - checkout.session.completed
    - customer.subscription.updated   (used for "Cancel subscription" in portal)
    - customer.subscription.deleted
    """
    init_stripe()

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    event_type = event.get("type", "")
    obj = event["data"]["object"]

    try:
        # ---------------------------------
        # 1) Checkout completed (activate)
        # ---------------------------------
        if event_type == "checkout.session.completed":
            session = obj
            stripe_sub_id = session.get("subscription")
            if not stripe_sub_id:
                return HttpResponse(status=200)

            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)

            md = session.get("metadata") or stripe_sub.get("metadata") or {}
            plan_code = (md.get("plan_code") or "basic").strip().lower()
            profile_id = md.get("profile_id")

            profile = Profile.objects.filter(pk=profile_id).first() if profile_id else None
            if not profile:
                profile = _find_profile_for_subscription(stripe_sub)
            if not profile:
                logger.warning("Webhook: cannot link checkout to profile (missing metadata/profile).")
                return HttpResponse(status=200)

            customer_id = session.get("customer") or stripe_sub.get("customer")
            if customer_id and hasattr(profile, "stripe_customer_id"):
                if profile.stripe_customer_id != customer_id:
                    profile.stripe_customer_id = customer_id
                    profile.save(update_fields=["stripe_customer_id"])

            plan = SubscriptionPlan.objects.filter(code=plan_code).first()
            if not plan:
                logger.warning("Webhook: plan not found in DB: %s", plan_code)
                return HttpResponse(status=200)

            stripe_status = (stripe_sub.get("status") or "").strip().lower()
            new_status = _map_status(stripe_status)

            cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
            cancel_at = _utc_from_ts(stripe_sub.get("cancel_at"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at"))
            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))

            existing = Subscription.objects.filter(profile=profile, stripe_subscription_id=stripe_sub_id).first()
            prev_status = existing.status if existing else None

            sub_obj, created = Subscription.objects.update_or_create(
                profile=profile,
                stripe_subscription_id=stripe_sub_id,
                defaults={
                    "plan": plan,
                    "status": new_status,
                    "stripe_customer_id": customer_id or "",
                    "current_period_end": current_period_end,
                    "cancel_at_period_end": cancel_at_period_end,
                    "cancel_at": cancel_at,
                    "canceled_at": canceled_at,
                },
            )

            # Populate started_at if missing
            if not sub_obj.started_at:
                sub_obj.started_at = timezone.now()
                sub_obj.save(update_fields=["started_at"])

            # Cancel local trial record if paid activated
            if plan_code != "trial":
                Subscription.objects.filter(
                    profile=profile,
                    plan__code="trial",
                    status=Subscription.STATUS_TRIALING,
                    stripe_subscription_id="",
                ).update(
                    status=Subscription.STATUS_CANCELED,
                    canceled_at=timezone.now(),
                    cancel_at=None,
                    cancel_at_period_end=False,
                )

            # Send confirmed email only on transition to active
            if prev_status != Subscription.STATUS_ACTIVE and sub_obj.status == Subscription.STATUS_ACTIVE:
                to_email = _profile_email(profile)
                if to_email:
                    ctx = _base_email_ctx(profile, plan.name)
                    _send_email(
                        "emails/subscription_confirmed.html",
                        "emails/subscription_confirmed.txt",
                        f"Your MintKit {plan.name} subscription is active ✅",
                        to_email,
                        ctx,
                    )

        # ------------------------------------------------------------
        # 2) Subscription updated (portal cancel => cancel_at_period_end)
        # ------------------------------------------------------------
        elif event_type == "customer.subscription.updated":
            stripe_sub = obj
            profile = _find_profile_for_subscription(stripe_sub)
            if not profile:
                return HttpResponse(status=200)

            sub_id = stripe_sub.get("id")
            existing = _find_local_subscription_by_stripe_id(sub_id) if sub_id else None

            stripe_status = (stripe_sub.get("status") or "").strip().lower()
            new_status = _map_status(stripe_status)

            cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
            cancel_at = _utc_from_ts(stripe_sub.get("cancel_at"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at"))
            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))
            customer_id = stripe_sub.get("customer")

            plan = _resolve_plan(stripe_sub, existing)
            if not plan:
                logger.warning("Webhook: could not resolve plan for subscription.updated sub_id=%s", sub_id)
                return HttpResponse(status=200)

            prev_status = existing.status if existing else None
            prev_cancel_flag = existing.cancel_at_period_end if existing else False

            sub_obj, _ = Subscription.objects.update_or_create(
                profile=profile,
                stripe_subscription_id=sub_id,
                defaults={
                    "plan": plan,
                    "status": new_status,
                    "stripe_customer_id": customer_id or "",
                    "current_period_end": current_period_end,
                    "cancel_at_period_end": cancel_at_period_end,
                    "cancel_at": cancel_at,
                    "canceled_at": canceled_at,
                },
            )

            # Email when user presses "Cancel subscription" (schedule end)
            if (not prev_cancel_flag) and cancel_at_period_end and new_status in (
                Subscription.STATUS_ACTIVE,
                Subscription.STATUS_TRIALING,
            ):
                to_email = _profile_email(profile)
                if to_email:
                    ctx = _base_email_ctx(profile, plan.name)
                    ctx.update(
                        {
                            "ends_on": current_period_end,
                            "manage_url": ctx["portal_url"],
                            "site_url": ctx["site_root"],
                        }
                    )
                    _send_email(
                        "emails/subscription_cancelled.html",
                        "emails/subscription_cancelled.txt",
                        "Your MintKit subscription will end (unless resumed)",
                        to_email,
                        ctx,
                    )

            # Email for immediate cancellation (status flips to canceled)
            if prev_status != Subscription.STATUS_CANCELED and sub_obj.status == Subscription.STATUS_CANCELED:
                to_email = _profile_email(profile)
                if to_email:
                    ctx = _base_email_ctx(profile, plan.name)
                    ctx.update(
                        {
                            "ends_on": current_period_end,
                            "manage_url": ctx["portal_url"],
                            "site_url": ctx["site_root"],
                        }
                    )
                    _send_email(
                        "emails/subscription_cancelled.html",
                        "emails/subscription_cancelled.txt",
                        "Your MintKit subscription has been cancelled",
                        to_email,
                        ctx,
                    )

        # ---------------------------------
        # 3) Subscription deleted (ended)
        # ---------------------------------
        elif event_type == "customer.subscription.deleted":
            stripe_sub = obj
            profile = _find_profile_for_subscription(stripe_sub)
            if not profile:
                return HttpResponse(status=200)

            sub_id = stripe_sub.get("id")
            existing = _find_local_subscription_by_stripe_id(sub_id) if sub_id else None

            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at")) or timezone.now()

            plan = _resolve_plan(stripe_sub, existing) if stripe_sub else (existing.plan if existing else None)

            if existing:
                existing.status = Subscription.STATUS_CANCELED
                existing.cancel_at_period_end = False
                existing.cancel_at = None
                existing.canceled_at = canceled_at
                if current_period_end:
                    existing.current_period_end = current_period_end
                existing.save(
                    update_fields=[
                        "status",
                        "cancel_at_period_end",
                        "cancel_at",
                        "canceled_at",
                        "current_period_end",
                    ]
                )
            else:
                if plan:
                    Subscription.objects.create(
                        profile=profile,
                        plan=plan,
                        status=Subscription.STATUS_CANCELED,
                        stripe_subscription_id=sub_id or "",
                        stripe_customer_id=(stripe_sub.get("customer") or ""),
                        current_period_end=current_period_end,
                        cancel_at_period_end=False,
                        cancel_at=None,
                        canceled_at=canceled_at,
                        started_at=timezone.now(),
                    )

            # Email when subscription actually ends/deletes
            to_email = _profile_email(profile)
            if to_email and plan:
                ctx = _base_email_ctx(profile, plan.name)
                ctx.update(
                    {
                        "ends_on": current_period_end,
                        "manage_url": ctx["portal_url"],
                        "site_url": ctx["site_root"],
                    }
                )
                _send_email(
                    "emails/subscription_cancelled.html",
                    "emails/subscription_cancelled.txt",
                    "Your MintKit subscription has ended",
                    to_email,
                    ctx,
                )

    except Exception:
        # Keep 200 so Stripe won’t spam retries, but log properly
        logger.exception("Stripe webhook processing failed for event=%s", event_type)

    return HttpResponse(status=200)
