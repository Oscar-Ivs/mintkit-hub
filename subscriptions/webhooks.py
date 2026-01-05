# subscriptions/webhooks.py
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan
from .stripe_service import init_stripe


def _map_stripe_status_to_local(stripe_status: str) -> str:
    """
    Map Stripe subscription statuses to the simplified local set.
    Keeps logic easy to explain in README/testing.
    """
    status = (stripe_status or "").lower()

    if status == "trialing":
        return Subscription.STATUS_TRIALING
    if status == "active":
        return Subscription.STATUS_ACTIVE
    if status in {"canceled", "unpaid", "incomplete_expired"}:
        return Subscription.STATUS_CANCELLED

    # fallback for anything else (past_due, incomplete, etc.)
    return Subscription.STATUS_EXPIRED


def _update_subscription_from_stripe(profile: Profile, plan: SubscriptionPlan, stripe_sub: dict, customer_id: str):
    period_end_ts = stripe_sub.get("current_period_end")
    period_end = None
    if period_end_ts:
        period_end = datetime.fromtimestamp(int(period_end_ts), tz=dt_timezone.utc)

    local_status = _map_stripe_status_to_local(stripe_sub.get("status", ""))

    Subscription.objects.update_or_create(
        stripe_subscription_id=stripe_sub.get("id", "") or "",
        defaults={
            "profile": profile,
            "plan": plan,
            "status": local_status,
            "stripe_customer_id": customer_id or "",
            "current_period_end": period_end,
        },
    )


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook endpoint.
    Add this URL in Stripe dashboard:
      https://<SITE_URL>/subscriptions/webhook/
    """
    stripe = init_stripe()

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=getattr(settings, "STRIPE_WEBHOOK_SECRET", ""),
        )
    except Exception:
        # Signature/payload failure -> 400 so Stripe retries while fixing config
        return HttpResponse(status=400)

    event_type = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    # 1) Checkout finished -> create/update local Subscription
    if event_type == "checkout.session.completed":
        if obj.get("mode") != "subscription":
            return HttpResponse(status=200)

        metadata = obj.get("metadata") or {}
        profile_id = metadata.get("profile_id") or obj.get("client_reference_id")
        plan_code = metadata.get("plan_code")

        if not profile_id or not plan_code:
            return HttpResponse(status=200)

        try:
            profile = Profile.objects.get(id=profile_id)
            plan = SubscriptionPlan.objects.get(code=plan_code)
        except (Profile.DoesNotExist, SubscriptionPlan.DoesNotExist):
            return HttpResponse(status=200)

        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer") or ""

        if not subscription_id:
            return HttpResponse(status=200)

        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        _update_subscription_from_stripe(profile, plan, stripe_sub, customer_id)
        return HttpResponse(status=200)

    # 2) Subscription changes -> keep local in sync
    if event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        subscription_id = obj.get("id", "")
        customer_id = obj.get("customer", "")

        # Best-effort: update the existing local subscription record
        local = Subscription.objects.filter(stripe_subscription_id=subscription_id).select_related("profile", "plan").first()
        if not local:
            return HttpResponse(status=200)

        stripe_sub = obj  # event already includes subscription object
        _update_subscription_from_stripe(local.profile, local.plan, stripe_sub, customer_id)
        return HttpResponse(status=200)

    return HttpResponse(status=200)
