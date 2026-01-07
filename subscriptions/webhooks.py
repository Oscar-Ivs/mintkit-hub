# subscriptions/webhooks.py
import datetime
import logging
from urllib.parse import urlsplit

import stripe
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan
from .stripe_service import init_stripe

logger = logging.getLogger(__name__)


def _utc_from_ts(ts):
    # Stripe timestamps are unix seconds; convert to timezone-aware UTC datetime
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


def _send_email(template_html, template_txt, subject, to_email, ctx):
    # Render and send an HTML + text email
    html_body = render_to_string(template_html, ctx)
    txt_body = render_to_string(template_txt, ctx)

    msg = EmailMultiAlternatives(subject=subject, body=txt_body, to=[to_email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


def _site_parts():
    """
    Build protocol/domain/site_root from SITE_URL.
    Templates for other emails often rely depend on consistent keys.
    """
    raw_site = (settings.SITE_URL or "").rstrip("/")
    parts = urlsplit(raw_site)

    if parts.scheme and parts.netloc:
        protocol = parts.scheme
        domain = parts.netloc
        site_root = f"{protocol}://{domain}"
        return protocol, domain, site_root

    # Fallback when SITE_URL is set without scheme
    domain = raw_site.replace("https://", "").replace("http://", "").split("/")[0]
    protocol = "https"
    site_root = f"{protocol}://{domain}" if domain else ""
    return protocol, domain, site_root


def _email_base_ctx(profile: Profile):
    protocol, domain, site_root = _site_parts()

    return {
        "first_name": profile.user.first_name or profile.user.username,

        # Keep keys consistent with your “confirmed” email context
        "protocol": protocol,
        "domain": domain,
        "site_root": site_root,

        # Common links used in email templates/footers
        "dashboard_url": f"{site_root}/dashboard/",
        "portal_url": f"{site_root}/subscriptions/portal/",
        "about_url": f"{site_root}/about/",
        "pricing_url": f"{site_root}/pricing/",
        "faq_url": f"{site_root}/faq/",
        "support_email": "support@mintkit.co.uk",
    }


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
    local = Subscription.objects.select_related("profile").filter(stripe_subscription_id=sub_id).first()
    return local.profile if local else None


def _map_stripe_status(stripe_status: str) -> str:
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


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook endpoint.
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
        # 1) Checkout completed
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

            new_status = _map_stripe_status(stripe_sub.get("status"))
            cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
            cancel_at = _utc_from_ts(stripe_sub.get("cancel_at"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at"))
            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))

            existing = Subscription.objects.filter(profile=profile, stripe_subscription_id=stripe_sub_id).first()
            prev_status = existing.status if existing else None

            sub_obj, _ = Subscription.objects.update_or_create(
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

            # Cancel local trial record if paid activated
            if plan_code != "trial":
                Subscription.objects.filter(
                    profile=profile,
                    plan__code="trial",
                    status=Subscription.STATUS_TRIALING,
                    stripe_subscription_id="",
                ).update(
                    status=Subscription.STATUS_CANCELED,
                    canceled_at=datetime.datetime.now(tz=datetime.timezone.utc),
                    cancel_at=None,
                    cancel_at_period_end=False,
                )

            # Send confirmed email only on transition to active
            if prev_status != Subscription.STATUS_ACTIVE and sub_obj.status == Subscription.STATUS_ACTIVE:
                to_email = profile.contact_email or profile.user.email
                if to_email:
                    ctx = _email_base_ctx(profile)
                    ctx.update({"plan_name": plan.name})

                    _send_email(
                        "emails/subscription_confirmed.html",
                        "emails/subscription_confirmed.txt",
                        f"Your MintKit {plan.name} subscription is active ✅",
                        to_email,
                        ctx,
                    )

        # 2) Subscription updated (cancel scheduled, resumed, etc.)
        elif event_type == "customer.subscription.updated":
            stripe_sub = obj
            profile = _find_profile_for_subscription(stripe_sub)
            if not profile:
                return HttpResponse(status=200)

            sub_id = stripe_sub.get("id")
            existing = Subscription.objects.filter(profile=profile, stripe_subscription_id=sub_id).first()

            customer_id = stripe_sub.get("customer")
            new_status = _map_stripe_status(stripe_sub.get("status"))
            cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
            cancel_at = _utc_from_ts(stripe_sub.get("cancel_at"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at"))
            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))

            md = stripe_sub.get("metadata") or {}
            plan_code = (md.get("plan_code") or (existing.plan.code if existing and existing.plan else "basic")).strip().lower()
            plan = SubscriptionPlan.objects.filter(code=plan_code).first()
            if not plan:
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

            # Cancellation scheduled email (cancel at period end)
            if (not prev_cancel_flag) and cancel_at_period_end and new_status == Subscription.STATUS_ACTIVE:
                to_email = profile.contact_email or profile.user.email
                if to_email:
                    ctx = _email_base_ctx(profile)
                    ctx.update(
                        {
                            "plan_name": plan.name,
                            "ends_on": current_period_end,
                            "manage_url": ctx.get("portal_url"),
                            "site_url": settings.SITE_URL,
                        }
                    )
                    _send_email(
                        "emails/subscription_cancelled.html",
                        "emails/subscription_cancelled.txt",
                        "Your MintKit subscription will end (unless resumed)",
                        to_email,
                        ctx,
                    )

            # Cancelled immediately (status switched to canceled)
            if prev_status != Subscription.STATUS_CANCELED and sub_obj.status == Subscription.STATUS_CANCELED:
                to_email = profile.contact_email or profile.user.email
                if to_email:
                    ctx = _email_base_ctx(profile)
                    ctx.update(
                        {
                            "plan_name": plan.name,
                            "ends_on": current_period_end,
                            "manage_url": ctx.get("portal_url"),
                            "site_url": settings.SITE_URL,
                        }
                    )
                    _send_email(
                        "emails/subscription_cancelled.html",
                        "emails/subscription_cancelled.txt",
                        "Your MintKit subscription has been cancelled",
                        to_email,
                        ctx,
                    )

        # 3) Subscription deleted (ended or cancelled immediately)
        elif event_type == "customer.subscription.deleted":
            stripe_sub = obj
            profile = _find_profile_for_subscription(stripe_sub)
            if not profile:
                return HttpResponse(status=200)

            sub_id = stripe_sub.get("id")
            existing = Subscription.objects.filter(profile=profile, stripe_subscription_id=sub_id).first()

            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at")) or datetime.datetime.now(tz=datetime.timezone.utc)

            # Prefer local plan when available (metadata is not always reliable on deleted events)
            plan = existing.plan if (existing and existing.plan) else None

            prev_status = existing.status if existing else None
            sub_obj = existing
            if sub_obj:
                sub_obj.status = Subscription.STATUS_CANCELED
                sub_obj.cancel_at_period_end = False
                sub_obj.cancel_at = None
                sub_obj.canceled_at = canceled_at
                sub_obj.current_period_end = current_period_end
                sub_obj.save(
                    update_fields=["status", "cancel_at_period_end", "cancel_at", "canceled_at", "current_period_end"]
                )

            # Send a cancellation email when Stripe actually deletes the subscription
            if prev_status != Subscription.STATUS_CANCELED:
                to_email = profile.contact_email or profile.user.email
                if to_email:
                    ctx = _email_base_ctx(profile)
                    ctx.update(
                        {
                            "plan_name": plan.name if plan else "Subscription",
                            "ends_on": current_period_end,
                            "manage_url": ctx.get("portal_url"),
                            "site_url": settings.SITE_URL,
                        }
                    )
                    _send_email(
                        "emails/subscription_cancelled.html",
                        "emails/subscription_cancelled.txt",
                        "Your MintKit subscription has been cancelled",
                        to_email,
                        ctx,
                    )

    except Exception:
        # Keep 200 so Stripe won’t spam retries, but log properly
        logger.exception("Stripe webhook processing failed for event=%s", event_type)

    return HttpResponse(status=200)
