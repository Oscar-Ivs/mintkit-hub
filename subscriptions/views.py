# subscriptions/views.py
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan

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
        started_at=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=TRIAL_DAYS),
    )

    messages.success(request, f"Free trial started ({TRIAL_DAYS} days). MintKit Studio is now unlocked.")
    return redirect("dashboard")
