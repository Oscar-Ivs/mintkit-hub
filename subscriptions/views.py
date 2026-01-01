# subscriptions/views.py
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan


TRIAL_DAYS = 14


@login_required
def start_trial(request):
    """
    Start a one-time free trial without Stripe.
    Creates a Subscription row with status trial/trialing and a fixed end date.
    """
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "business_name": request.user.username,
            "contact_email": getattr(request.user, "email", "") or "",
        },
    )

    # Block repeat trials: any existing subscription means trial was already used
    if Subscription.objects.filter(profile=profile).exists():
        messages.warning(request, "Free trial was already used for this account.")
        return redirect("pricing")

    # Pick a plan to attach to the subscription
    trial_plan = (
        SubscriptionPlan.objects.filter(name__icontains="trial").first()
        or SubscriptionPlan.objects.first()
    )

    if not trial_plan:
        messages.error(request, "No subscription plans exist yet. Add one in Django admin first.")
        return redirect("pricing")

    Subscription.objects.create(
        profile=profile,
        plan=trial_plan,
        status="trialing",  # dashboard logic checks trial/trialing
        started_at=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=TRIAL_DAYS),
    )

    messages.success(request, f"Free trial started ({TRIAL_DAYS} days). MintKit Studio is now unlocked.")
    return redirect("dashboard")
