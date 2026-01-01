# accounts/views.py
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date, datetime


from storefronts.models import Storefront
from subscriptions.models import Subscription

from .emails import send_welcome_email, _brand_links, _email_asset_urls
from .forms import CustomUserCreationForm, ProfileForm, AccountEmailForm
from .models import Profile

logger = logging.getLogger(__name__)


def register(request):
    """
    Register a new user and create a matching Profile.
    Email failures must not block registration.
    """
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            Profile.objects.get_or_create(
                user=user,
                defaults={
                    "business_name": user.username,
                    "contact_email": getattr(user, "email", "") or "",
                },
            )

            try:
                send_welcome_email(user, request=request)
            except Exception:
                logger.exception("Welcome email failed for user_id=%s", user.id)

            messages.success(request, "Your account has been created. You can now log in.")
            return redirect("login")
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


def logout_view(request):
    """Log the user out and redirect to the homepage."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def dashboard(request):
    """Main dashboard for the logged-in user."""
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "business_name": request.user.username,
            "contact_email": getattr(request.user, "email", "") or "",
        },
    )

    storefront = Storefront.objects.filter(profile=profile).first()

    subscription = (
        Subscription.objects.filter(profile=profile)
        .order_by("-started_at")
        .first()
    )

    # Compute access flags once; keep template logic simple.
    studio_access = False
    trial_expired = False

    def _to_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None

    today = timezone.localdate()

    if subscription:
        if subscription.status == "active":
            studio_access = True

        elif subscription.status in ("trial", "trialing"):
            end_date = _to_date(getattr(subscription, "current_period_end", None))

            if end_date and end_date >= today:
                studio_access = True
            else:
                trial_expired = True
                studio_access = False

    context = {
        "profile": profile,
        "storefront": storefront,
        "subscription": subscription,
        "studio_access": studio_access,
        "trial_expired": trial_expired,
    }
    return render(request, "accounts/dashboard.html", context)

@login_required
def edit_profile(request):
    """
    Allow the logged-in user to edit:
    - business profile (Profile)
    - account email (User.email shown in Django admin)
    """
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "business_name": request.user.username,
            "contact_email": getattr(request.user, "email", "") or "",
        },
    )

    if request.method == "POST":
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        email_form = AccountEmailForm(request.POST, instance=request.user)

        if profile_form.is_valid() and email_form.is_valid():
            profile_form.save()
            email_form.save()

            messages.success(request, "Your profile has been updated.")
            return redirect("dashboard")
    else:
        profile_form = ProfileForm(instance=profile)
        email_form = AccountEmailForm(instance=request.user)

    # "form" kept for backwards compatibility with templates using {{ form }}
    return render(
        request,
        "accounts/edit_profile.html",
        {
            "profile": profile,
            "form": profile_form,
            "profile_form": profile_form,
            "email_form": email_form,
        },
    )


def email_preview(request, kind: str):
    """
    Dev-only email preview in the browser.
    Visit:
      /accounts/email-preview/welcome/
      /accounts/email-preview/subscription/
    """
    if not settings.DEBUG:
        return HttpResponse("Not found", status=404)

    links = _brand_links(request)  # uses request.build_absolute_uri
    assets = _email_asset_urls(request)  # absolute static URLs

    context = {
        "user_name": "Preview User",
        "year": timezone.now().year,
        "site_root": links.site_root,
        "dashboard_url": links.dashboard_url,
        "about_url": links.about_url,
        "pricing_url": links.pricing_url,
        "faq_url": links.faq_url,
        "studio_access": studio_access,
        "trial_expired": trial_expired,
        **assets,
    }

    if kind == "welcome":
        html = render_to_string("emails/welcome.html", context)
        return HttpResponse(html)

    if kind == "subscription":
        html = render_to_string("emails/subscription_confirmed.html", context)
        return HttpResponse(html)

    return HttpResponse("Unknown preview type", status=404)
