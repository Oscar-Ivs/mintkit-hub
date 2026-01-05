# subscriptions/webhooks.py
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan
from .stripe_service import init_stripe


def _map_stripe_status_to_local(stripe_status: str) -> str:
    """
    Map Stripe subscription statuses to the local simplified set.
    """
    status = (stripe_status or "").lower()

    if status == "trialing":
        return Subscription.STATUS_TRIALING
    if status == "active":
        return Subscription.STATUS_ACTIVE
    if status == "past_due":
        return Subscription.STATUS_PAST_DUE
    if status in {"canceled", "unpaid", "incomplete_expired"}:
        return Subscription.STATUS_CANCELED
    if status == "incomplete":
        return Subscription.STATUS_INCOMPLETE

    # Default fallback keeps UI consistent
    return Subscription.STATUS_INCOMPLETE


def _update_subscription_from_stripe(
    *,
    profile: Profile,
    plan: SubscriptionPlan,
    stripe_sub: dict,
    customer_id: str,
) -> None:
    sub_id = stripe_sub.get("id") or ""
    if not sub_id:
        return

    period_end_ts = stripe_sub.get("current_period_end")
    period_end = None
    if period_end_ts:
        period_end = datetime.fromtimestamp(int(period_end_ts), tz=dt_timezone.utc)

    local_status = _map_stripe_status_to_local(stripe_sub.get("status", ""))

    Subscription.objects.update_or_create(
        stripe_subscription_id=sub_id,
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

    Stripe dashboard -> Developers -> Webhooks:
      Endpoint URL: https://mintkit.co.uk/subscriptions/webhook/

    Enable these events:
      - checkout.session.completed
      - customer.subscription.updated
      - customer.subscription.deleted
    """
    stripe = init_stripe()

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "") or ""
    if not webhook_secret:
        # Misconfigured env/settings -> tell Stripe to retry
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret,
        )
    except Exception:
        return HttpResponse(status=400)

    event_type = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    # 1) Checkout finished (subscription created)
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
        _update_subscription_from_stripe(profile=profile, plan=plan, stripe_sub=stripe_sub, customer_id=customer_id)
        return HttpResponse(status=200)

    # 2) Subscription changes (status/period end updates, cancels)
    if event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        subscription_id = obj.get("id", "")
        customer_id = obj.get("customer", "")

        local = (
            Subscription.objects
            .filter(stripe_subscription_id=subscription_id)
            .select_related("profile", "plan")
            .first()
        )
        if not local:
            return HttpResponse(status=200)

        _update_subscription_from_stripe(profile=local.profile, plan=local.plan, stripe_sub=obj, customer_id=customer_id)
        return HttpResponse(status=200)

    return HttpResponse(status=200)
