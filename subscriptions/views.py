# subscriptions/views.py
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan
from .stripe_service import init_stripe, get_stripe_price_id

from django.shortcuts import redirect

def subscriptions_home(request):
    # Redirect /subscriptions/ somewhere useful
    return redirect("pricing")


TRIAL_DAYS = 14


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


@login_required
def start_trial(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "business_name": request.user.username,
            "contact_email": getattr(request.user, "email", "") or "",
        },
    )

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
        status="trialing",
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

    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "business_name": request.user.username,
            "contact_email": getattr(request.user, "email", "") or "",
        },
    )

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
    User feedback page after Stripe redirects back.
    Webhook is the source of truth; this is just UI feedback.
    """
    messages.success(request, "Payment complete. Subscription will appear on your dashboard shortly.")
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
