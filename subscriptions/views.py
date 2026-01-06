# subscriptions/views.py
import datetime
import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan
from .stripe_service import init_stripe, get_stripe_price_id

logger = logging.getLogger(__name__)


def _active_paid_subscription_exists(profile: Profile) -> bool:
    """
    True if there is any active paid subscription (Stripe-backed).
    """
    return (
        Subscription.objects.filter(profile=profile)
        .exclude(stripe_subscription_id="")
        .exclude(status=Subscription.STATUS_CANCELED)
        .exists()
    )


def _trial_used(profile: Profile) -> bool:
    """
    Treat trial as used if:
      - a trial subscription exists (even canceled), OR
      - any paid subscription exists (even canceled)
    """
    return (
        Subscription.objects.filter(profile=profile, plan__code="trial").exists()
        or Subscription.objects.filter(profile=profile).exclude(plan__code="trial").exists()
    )


def _send_subscription_email_confirmed(profile: Profile, plan: SubscriptionPlan) -> None:
    """
    Sends the styled subscription confirmed email (HTML + text fallback).
    """
    to_email = profile.contact_email or profile.user.email
    if not to_email:
        return

    ctx = {
        "first_name": profile.user.first_name or profile.user.username,
        "plan_name": plan.name,
        "manage_url": f"{settings.SITE_URL}{reverse('subscriptions_billing_portal')}",
        "site_url": settings.SITE_URL,
        "support_email": "support@mintkit.co.uk",
    }

    subject = f"Your MintKit {plan.name} subscription is active ✅"
    html_body = render_to_string("emails/subscription_confirmed.html", ctx)
    text_body = render_to_string("emails/subscription_confirmed.txt", ctx)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[to_email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


@login_required
def start_trial(request):
    profile = request.user.profile

    if _trial_used(profile):
        messages.error(request, "Free trial has already been used on this account.")
        return redirect("pricing")

    trial_plan = SubscriptionPlan.objects.filter(code="trial", is_active=True).first()
    if not trial_plan:
        messages.error(request, "Trial plan is not configured.")
        return redirect("pricing")

    now = timezone.now()
    trial_ends = now + datetime.timedelta(days=14)

    Subscription.objects.create(
        profile=profile,
        plan=trial_plan,
        status=Subscription.STATUS_TRIALING,
        current_period_end=trial_ends,
        stripe_customer_id="",
        stripe_subscription_id="",
        cancel_at_period_end=False,
        cancel_at=None,
        canceled_at=None,
    )

    messages.success(request, "Free trial started! Enjoy MintKit Hub 🚀")
    return redirect("dashboard")


@login_required
def checkout(request, plan_code: str):
    """
    Creates a Stripe Checkout session.
    """
    profile = request.user.profile

    # Billing cycle (for annual toggle)
    billing = request.GET.get("billing", "monthly").lower().strip()
    if billing not in ("monthly", "annual"):
        billing = "monthly"

    # Prevent buying again if already active paid
    if _active_paid_subscription_exists(profile) and plan_code in ("basic", "pro"):
        messages.info(request, "Subscription is already active. Manage billing from your dashboard.")
        return redirect("dashboard")

    if plan_code == "trial":
        messages.info(request, "Trial doesn’t require payment.")
        return redirect("pricing")

    plan = SubscriptionPlan.objects.filter(code=plan_code, is_active=True).first()
    if not plan:
        messages.error(request, "That plan is not available.")
        return redirect("pricing")

    init_stripe()
    price_id = get_stripe_price_id(plan_code, billing=billing)

    success_url = f"{settings.SITE_URL}{reverse('subscriptions_checkout_success')}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.SITE_URL}{reverse('subscriptions_checkout_cancel')}"

    # Ensure Stripe subscription also carries metadata (critical for webhook linking)
    subscription_data = {
        "metadata": {
            "profile_id": str(profile.id),
            "plan_code": plan_code,
            "billing": billing,
        }
    }

    session_params = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(profile.id),
        "metadata": {
            "profile_id": str(profile.id),
            "plan_code": plan_code,
            "billing": billing,
        },
        "subscription_data": subscription_data,
    }

    # Reuse existing Stripe customer if known
    customer_id = getattr(profile, "stripe_customer_id", "") or ""
    if customer_id:
        session_params["customer"] = customer_id
    else:
        session_params["customer_email"] = profile.contact_email or request.user.email

    session = stripe.checkout.Session.create(**session_params)
    return redirect(session.url, permanent=False)


@login_required
def checkout_success(request):
    """
    Landing page after Stripe checkout.
    Sync local DB and (if needed) send email once.
    """
    session_id = request.GET.get("session_id")
    if not session_id:
        messages.error(request, "Missing Stripe session id.")
        return redirect("pricing")

    init_stripe()
    profile = request.user.profile

    session = stripe.checkout.Session.retrieve(session_id)
    stripe_subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    # Some edge cases can return no subscription id; avoid a 500
    if not stripe_subscription_id:
        messages.error(request, "Stripe did not return a subscription id for this session.")
        return redirect("pricing")

    if customer_id and hasattr(profile, "stripe_customer_id"):
        if profile.stripe_customer_id != customer_id:
            profile.stripe_customer_id = customer_id
            profile.save(update_fields=["stripe_customer_id"])

    # Determine plan code from metadata
    md = session.get("metadata") or {}
    plan_code = (md.get("plan_code") or "basic").strip().lower()

    plan = SubscriptionPlan.objects.filter(code=plan_code).first()
    if not plan:
        messages.error(request, "Subscription plan not found in database.")
        return redirect("pricing")

    # Retrieve Stripe subscription for period end + cancel flags
    stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
    stripe_status = (stripe_sub.get("status") or "").strip().lower()

    cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
    cancel_at = stripe_sub.get("cancel_at")          # scheduled cancellation time
    canceled_at = stripe_sub.get("canceled_at")      # actual cancellation time (if canceled)

    # Map Stripe status to local values without collapsing everything to "canceled"
    status_map = {
        "active": Subscription.STATUS_ACTIVE,
        "trialing": Subscription.STATUS_TRIALING,
        "past_due": Subscription.STATUS_PAST_DUE,
        "unpaid": Subscription.STATUS_PAST_DUE,
        "incomplete": Subscription.STATUS_INCOMPLETE,
        "incomplete_expired": Subscription.STATUS_INCOMPLETE,
        "canceled": Subscription.STATUS_CANCELED,
        "cancelled": Subscription.STATUS_CANCELED,  # defensive spelling
    }
    local_status = status_map.get(stripe_status, Subscription.STATUS_CANCELED)

    current_period_end = stripe_sub.get("current_period_end")
    current_period_end_dt = (
        datetime.datetime.fromtimestamp(current_period_end, tz=datetime.timezone.utc)
        if current_period_end
        else None
    )

    cancel_at_dt = (
        datetime.datetime.fromtimestamp(cancel_at, tz=datetime.timezone.utc)
        if cancel_at
        else None
    )
    canceled_at_dt = (
        datetime.datetime.fromtimestamp(canceled_at, tz=datetime.timezone.utc)
        if canceled_at
        else None
    )

    existing = Subscription.objects.filter(profile=profile, stripe_subscription_id=stripe_subscription_id).first()
    prev_status = existing.status if existing else None

    sub_obj, _created = Subscription.objects.update_or_create(
        profile=profile,
        stripe_subscription_id=stripe_subscription_id,
        defaults={
            "plan": plan,
            "status": local_status,
            "stripe_customer_id": customer_id or "",
            "current_period_end": current_period_end_dt,
            "cancel_at_period_end": cancel_at_period_end,
            "cancel_at": cancel_at_dt,
            "canceled_at": canceled_at_dt,
        },
    )

    # If a paid subscription became active, cancel any existing local trial record
    if plan_code != "trial":
        Subscription.objects.filter(
            profile=profile,
            plan__code="trial",
            status=Subscription.STATUS_TRIALING,
            stripe_subscription_id="",
        ).update(status=Subscription.STATUS_CANCELED, canceled_at=timezone.now(), cancel_at=None, cancel_at_period_end=False)

    # Send confirmation email only when transitioning into active
    if prev_status != Subscription.STATUS_ACTIVE and sub_obj.status == Subscription.STATUS_ACTIVE:
        try:
            _send_subscription_email_confirmed(profile, plan)
        except Exception:
            logger.exception("Failed sending subscription confirmed email")

    messages.success(request, "Subscription confirmed! Welcome aboard 🚀")
    return redirect("dashboard")


@login_required
def checkout_cancel(request):
    messages.info(request, "Checkout cancelled. No payment was taken.")
    return redirect("pricing")


@login_required
def billing_portal(request):
    """
    Opens Stripe Billing Portal for the user's Stripe customer.
    """
    init_stripe()
    profile = request.user.profile

    customer_id = getattr(profile, "stripe_customer_id", "") or ""

    if not customer_id:
        # fallback: try from any subscription
        latest = (
            Subscription.objects.filter(profile=profile)
            .exclude(stripe_customer_id="")
            .order_by("-created_at")
            .first()
        )
        customer_id = latest.stripe_customer_id if latest else ""

    if not customer_id:
        messages.error(request, "No Stripe customer found for this account.")
        return redirect("dashboard")

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.SITE_URL}{reverse('dashboard')}",
    )
    return redirect(portal_session.url, permanent=False)
