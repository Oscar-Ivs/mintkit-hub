# core/views.py
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from accounts.models import Profile
from subscriptions.models import Subscription


def _to_date(value):
    """Convert a date/datetime to a date object, otherwise return None."""
    if value is None:
        return None

    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()

    if isinstance(value, date):
        return value

    return None


def _studio_access(subscription):
    """Return True when Studio access should be granted."""
    if not subscription:
        return False

    status = (getattr(subscription, "status", "") or "").lower()
    today = timezone.localdate()

    if status == "active":
        return True

    if status in {"trial", "trialing"}:
        end_date = _to_date(getattr(subscription, "current_period_end", None))
        if end_date is None:
            return True
        return end_date >= today

    return False


def home(request):
    """Public landing page for MintKit Hub."""
    return render(request, "core/home.html")


def about(request):
    """Simple About page stub."""
    return render(request, "core/about.html")


def pricing(request):
    """
    Pricing page.

    Adds trial flags so the template can show:
    - eligible
    - active (with end date)
    - expired (trial already used)
    """
    trial_active = False
    trial_expired = False
    trial_end = None

    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                "business_name": request.user.username,
                "contact_email": getattr(request.user, "email", "") or "",
            },
        )

        subscription = (
            Subscription.objects.filter(profile=profile)
            .order_by("-started_at")
            .first()
        )

        if subscription:
            status = (subscription.status or "").lower()
            if status in {"trial", "trialing"}:
                trial_end = getattr(subscription, "current_period_end", None)
                today = timezone.localdate()

                if trial_end:
                    end_date = trial_end.date()
                    trial_active = end_date >= today
                    trial_expired = end_date < today
                else:
                    # No end date stored => treat as active trial
                    trial_active = True

    context = {
        "trial_active": trial_active,
        "trial_expired": trial_expired,
        "trial_end": trial_end,
    }
    return render(request, "core/pricing.html", context)

def faq(request):
    """Simple FAQ page stub."""
    return render(request, "core/faq.html")


@login_required
def studio(request):
    """
    Redirect helper to MintKit Studio.

    Access rule:
    - Active subscription => allowed
    - Trial/trialing => allowed only while trial end date is not in the past
    - Otherwise => redirect to Pricing
    """
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "business_name": request.user.username,
            "contact_email": getattr(request.user, "email", "") or "",
        },
    )

    subscription = (
        Subscription.objects.filter(profile=profile)
        .order_by("-started_at")
        .first()
    )

    if not _studio_access(subscription):
        messages.warning(request, "MintKit Studio is locked. Start a trial or plan to continue.")
        return redirect("pricing")

    STUDIO_URL = "https://mintkit-smr.caffeine.xyz"  # change when ready
    return redirect(STUDIO_URL)
