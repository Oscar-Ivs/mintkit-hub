# subscriptions/views.py
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan
from .stripe_service import init_stripe, get_stripe_price_id
from .webhooks import _update_subscription_from_stripe  # reuse the same sync logic as webhook


TRIAL_DAYS = 14


def subscriptions_home(request):
    # Redirect /subscriptions/ somewhere useful
    return redirect("pricing")


def _get_or_create_profile(user) -> Profile:
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={
            "business_name": user.username,
            "contact_email": getattr(user, "email", "") or "",
        },
    )
    return profile


def _trial_is_active(subscription) -> bool:
    if not subscription:
        return False

    status = (subscription.status or "").lower()
    if status not in {"trial", "trialing"}:
        return False

    end = getattr(subscription, "current_period_end", None)
    if end is None:
        return True

    # current_period_end might be date or datetime
    if hasattr(end, "date"):
        try:
            end = end.date()
        except TypeError:
            pass

    return end >= timezone.localdate()


def _active_paid_subscription_exists(profile: Profile) -> bool:
    # Paid = has Stripe subscription id, and is not canceled
    return (
        Subscription.objects.filter(profile=profile)
        .exclude(stripe_subscription_id="")
        .exclude(status=Subscription.STATUS_CANCELED)
        .exists()
    )


@login_required
def start_trial(request):
    profile = _get_or_create_profile(request.user)

    existing = Subscription.objects.filter(profile=profile).order_by("-started_at").first()

    # Already has active trial
    if existing and _trial_is_active(existing):
        messages.info(request, "Your free trial is already active.")
        return redirect("dashboard")

    # Any existing subscription record means trial was already used (simple rule for now)
    if existing:
        messages.warning(request, "Your free trial has already been used.")
        return redirect("pricing")

    trial_plan = (
        SubscriptionPlan.objects.filter(name__icontains="trial").first()
        or SubscriptionPlan.objects.first()
    )

    if not trial_plan:
        messages.error(request, "No subscription plans found. Add one in Django admin first.")
        return redirect("pricing")

    Subscription.objects.create(
        profile=profile,
        plan=trial_plan,
        status=Subscription.STATUS_TRIALING,
        current_period_end=timezone.now() + timedelta(days=TRIAL_DAYS),
    )

    messages.success(request, f"Free trial started ({TRIAL_DAYS} days). MintKit Studio is now unlocked.")
    return redirect("dashboard")


@login_required
def checkout(request, plan_code: str):
    """
    Starts Stripe Checkout (subscription mode) and redirects to Stripe-hosted page.
    """
    stripe = init_stripe()
    profile = _get_or_create_profile(request.user)

    # Block duplicate payments even if the Pricing button is still visible
    if _active_paid_subscription_exists(profile):
        messages.info(request, "An active subscription already exists. Manage it in the billing portal.")
        return redirect("subscriptions_billing_portal")

    plan = get_object_or_404(SubscriptionPlan, code=plan_code, is_active=True)
    price_id = get_stripe_price_id(plan.code, fallback_price_id=plan.stripe_price_id)

    success_url = request.build_absolute_uri(reverse("subscriptions_checkout_success"))
    success_url = f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = request.build_absolute_uri(reverse("subscriptions_checkout_cancel"))

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=str(profile.id),
        customer_email=(request.user.email or None),
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "profile_id": str(profile.id),
            "plan_code": plan.code,
        },
    )

    return redirect(session.url)


@login_required
def checkout_success(request):
    """
    Sync subscription after Stripe redirects back.
    Webhook remains the source of truth, but this makes the dashboard correct immediately.
    """
    session_id = request.GET.get("session_id", "")
    if not session_id:
        messages.success(request, "Payment complete. Subscription will appear on your dashboard shortly.")
        return redirect("dashboard")

    stripe = init_stripe()
    profile = _get_or_create_profile(request.user)

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        messages.success(request, "Payment complete. Subscription will appear on your dashboard shortly.")
        return redirect("dashboard")

    meta = session.get("metadata") or {}
    session_profile_id = meta.get("profile_id") or session.get("client_reference_id") or ""
    if str(session_profile_id) != str(profile.id):
        messages.warning(request, "Payment completed, but it could not be linked to this account.")
        return redirect("dashboard")

    plan_code = meta.get("plan_code") or ""
    subscription_id = session.get("subscription") or ""
    customer_id = session.get("customer") or ""

    if not plan_code or not subscription_id:
        messages.success(request, "Payment complete. Subscription will appear on your dashboard shortly.")
        return redirect("dashboard")

    try:
        plan = SubscriptionPlan.objects.get(code=plan_code, is_active=True)
        stripe_sub = stripe.Subscription.retrieve(subscription_id)

        # Create/update local subscription row (same mapping as webhook)
        _update_subscription_from_stripe(
            profile=profile,
            plan=plan,
            stripe_sub=stripe_sub,
            customer_id=customer_id,
        )

        # End local trial record so dashboard stops showing trial
        Subscription.objects.filter(
            profile=profile,
            stripe_subscription_id="",
            status=Subscription.STATUS_TRIALING,
        ).update(status=Subscription.STATUS_CANCELED)

        # Confirmation email (console backend prints to terminal if enabled)
        to_email = request.user.email or profile.contact_email or ""
        if to_email:
            send_mail(
                subject="MintKit subscription confirmed",
                message=f"Thanks for subscribing to MintKit ({plan.name}). Your access is now active.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
                recipient_list=[to_email],
                fail_silently=True,
            )

    except Exception:
        # Avoid blocking the user; webhook can still sync later
        pass

    messages.success(request, "Payment complete. Your subscription is now active.")
    return redirect("dashboard")


@login_required
def checkout_cancel(request):
    messages.info(request, "Checkout cancelled. No payment was taken.")
    return redirect("pricing")


@login_required
def billing_portal(request):
    """
    Redirects the user to Stripe Billing Portal to manage/cancel subscription.
    """
    stripe = init_stripe()
    profile = Profile.objects.filter(user=request.user).first()

    if not profile:
        messages.error(request, "Profile not found.")
        return redirect("dashboard")

    sub = (
        Subscription.objects.filter(profile=profile)
        .exclude(stripe_customer_id="")
        .order_by("-started_at")
        .first()
    )

    if not sub or not sub.stripe_customer_id:
        messages.warning(request, "No Stripe customer found for this account yet.")
        return redirect("pricing")

    return_url = request.build_absolute_uri(reverse("dashboard"))
    portal = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url,
    )
    return redirect(portal.url)
