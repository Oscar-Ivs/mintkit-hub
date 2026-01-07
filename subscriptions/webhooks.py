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


# ----------------------------
# Helpers
# ----------------------------
def _utc_from_ts(ts):
    """Stripe timestamps are unix seconds; convert to timezone-aware UTC datetime."""
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


def _site_parts():
    """
    Derive protocol/domain/site_root from SITE_URL.
    Works for https://mintkit.co.uk and http://127.0.0.1:8000.
    """
    raw_site = (getattr(settings, "SITE_URL", "") or "").rstrip("/") or "http://127.0.0.1:8000"
    parts = urlsplit(raw_site)

    if parts.scheme and parts.netloc:
        protocol = parts.scheme
        domain = parts.netloc
        site_root = f"{protocol}://{domain}"
    else:
        # Fallback if SITE_URL was set without scheme
        domain = raw_site.replace("https://", "").replace("http://", "").split("/")[0]
        protocol = "https"
        site_root = f"{protocol}://{domain}"

    return protocol, domain, site_root


def _base_email_ctx(profile, plan_name):
    """Context shared by all subscription emails (matches base_email.html expectations)."""
    protocol, domain, site_root = _site_parts()

    return {
        "first_name": profile.user.first_name or profile.user.username,
        "plan_name": plan_name,
        "protocol": protocol,
        "domain": domain,
        "site_root": site_root,
        # Correct dashboard path for this project
        "dashboard_url": f"{site_root}/accounts/dashboard/",
        "portal_url": f"{site_root}/subscriptions/portal/",
        # Footer / support
        "support_email": "support@mintkit.co.uk",
        "about_url": f"{site_root}/about/",
        "pricing_url": f"{site_root}/pricing/",
        "faq_url": f"{site_root}/faq/",
    }


def _send_email(template_html, template_txt, subject, to_email, ctx):
    """Render & send email; errors are logged but won't fail the webhook."""
    try:
        html_body = render_to_string(template_html, ctx)
        txt_body = render_to_string(template_txt, ctx)

        msg = EmailMultiAlternatives(subject=subject, body=txt_body, to=[to_email])
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)

        logger.info("Email sent: subject=%s to=%s", subject, to_email)
    except Exception:
        logger.exception("Email send failed: subject=%s to=%s", subject, to_email)


def _find_local_subscription_by_stripe_id(stripe_sub_id):
    return (
        Subscription.objects.select_related("profile", "plan")
        .filter(stripe_subscription_id=stripe_sub_id)
        .order_by("-started_at")
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

    local = _find_local_subscription_by_stripe_id(stripe_sub.get("id"))
    return local.profile if local else None


def _resolve_plan(plan_code, local_sub=None):
    """
    Resolve plan from:
    1) metadata plan_code, or
    2) existing local subscription plan.
    """
    if plan_code:
        plan = SubscriptionPlan.objects.filter(code=plan_code).first()
        if plan:
            return plan

    if local_sub and getattr(local_sub, "plan_id", None):
        return local_sub.plan

    return None


def _map_stripe_status(stripe_status):
    stripe_status = (stripe_status or "").strip().lower()
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
    return status_map.get(stripe_status, Subscription.STATUS_CANCELED)


def _profile_email(profile):
    return (getattr(profile, "contact_email", "") or "").strip() or (profile.user.email or "").strip()


# ----------------------------
# Webhook
# ----------------------------
@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe webhook endpoint."""
    init_stripe()

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    event_type = event.get("type", "")
    obj = event["data"]["object"]

    try:
        # ------------------------------------------------------------
        # 1) Checkout completed (create/update local subscription)
        # ------------------------------------------------------------
        if event_type == "checkout.session.completed":
            session = obj
            stripe_sub_id = session.get("subscription")
            if not stripe_sub_id:
                return HttpResponse(status=200)

            stripe_sub = stripe.Subscription.retrieve(
                stripe_sub_id,
                expand=["items.data.price"],
            )

            md = session.get("metadata") or stripe_sub.get("metadata") or {}
            plan_code = (md.get("plan_code") or "basic").strip().lower()
            profile_id = md.get("profile_id")

            profile = Profile.objects.filter(pk=profile_id).first() if profile_id else None
            if not profile:
                profile = _find_profile_for_subscription(stripe_sub)

            if not profile:
                logger.warning("Webhook: cannot link checkout to profile (missing metadata/profile).")
                return HttpResponse(status=200)

            customer_id = session.get("customer") or stripe_sub.get("customer") or ""
            if customer_id and hasattr(profile, "stripe_customer_id"):
                if profile.stripe_customer_id != customer_id:
                    profile.stripe_customer_id = customer_id
                    profile.save(update_fields=["stripe_customer_id"])

            plan = _resolve_plan(plan_code)
            if not plan:
                logger.warning("Webhook: plan not found in DB: %s", plan_code)
                return HttpResponse(status=200)

            stripe_status = stripe_sub.get("status")
            new_status = _map_stripe_status(stripe_status)

            cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
            cancel_at = _utc_from_ts(stripe_sub.get("cancel_at"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at"))
            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))

            existing = _find_local_subscription_by_stripe_id(stripe_sub_id)
            prev_status = existing.status if existing else None

            sub_obj, _ = Subscription.objects.update_or_create(
                profile=profile,
                stripe_subscription_id=stripe_sub_id,
                defaults={
                    "plan": plan,
                    "status": new_status,
                    "stripe_customer_id": customer_id,
                    "current_period_end": current_period_end,
                    "cancel_at_period_end": cancel_at_period_end,
                    "cancel_at": cancel_at,
                    "canceled_at": canceled_at,
                },
            )

            # Cancel local trial record if a paid plan activated
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

            # Send confirmed email only on transition to ACTIVE
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
        # 2) Subscription updated (scheduled cancel, resume, status change)
        # ------------------------------------------------------------
        elif event_type == "customer.subscription.updated":
            stripe_sub = obj
            sub_id = stripe_sub.get("id")

            existing = _find_local_subscription_by_stripe_id(sub_id)
            profile = existing.profile if existing else _find_profile_for_subscription(stripe_sub)

            if not profile:
                return HttpResponse(status=200)

            md = stripe_sub.get("metadata") or {}
            plan_code = (md.get("plan_code") or (existing.plan.code if existing and existing.plan else "basic")).strip().lower()
            plan = _resolve_plan(plan_code, existing)
            if not plan:
                return HttpResponse(status=200)

            stripe_status = stripe_sub.get("status")
            new_status = _map_stripe_status(stripe_status)

            cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
            cancel_at = _utc_from_ts(stripe_sub.get("cancel_at"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at"))
            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))
            customer_id = stripe_sub.get("customer") or ""

            prev_status = existing.status if existing else None
            prev_cancel_flag = existing.cancel_at_period_end if existing else False

            sub_obj, _ = Subscription.objects.update_or_create(
                profile=profile,
                stripe_subscription_id=sub_id,
                defaults={
                    "plan": plan,
                    "status": new_status,
                    "stripe_customer_id": customer_id,
                    "current_period_end": current_period_end,
                    "cancel_at_period_end": cancel_at_period_end,
                    "cancel_at": cancel_at,
                    "canceled_at": canceled_at,
                },
            )

            # Email: cancellation scheduled (user clicked cancel, but subscription still active until period end)
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

            # Email: cancelled immediately (status moved to canceled)
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

        # ------------------------------------------------------------
        # 3) Subscription deleted (ended OR cancelled immediately)
        # ------------------------------------------------------------
        elif event_type == "customer.subscription.deleted":
            stripe_sub = obj
            sub_id = stripe_sub.get("id")

            existing = _find_local_subscription_by_stripe_id(sub_id)
            profile = existing.profile if existing else _find_profile_for_subscription(stripe_sub)
            if not profile:
                return HttpResponse(status=200)

            md = stripe_sub.get("metadata") or {}
            plan_code = (md.get("plan_code") or (existing.plan.code if existing and existing.plan else "basic")).strip().lower()
            plan = _resolve_plan(plan_code, existing)

            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at")) or timezone.now()

            # Update local record if it exists
            if existing:
                existing.status = Subscription.STATUS_CANCELED
                existing.cancel_at_period_end = False
                existing.cancel_at = None
                existing.canceled_at = canceled_at
                existing.current_period_end = current_period_end or existing.current_period_end
                existing.save(
                    update_fields=[
                        "status",
                        "cancel_at_period_end",
                        "cancel_at",
                        "canceled_at",
                        "current_period_end",
                    ]
                )

            # Email: always notify on DELETE events
            to_email = _profile_email(profile)
            if to_email:
                plan_name = plan.name if plan else "subscription"
                ctx = _base_email_ctx(profile, plan_name)
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
