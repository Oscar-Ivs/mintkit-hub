# accounts/views.py
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from storefronts.models import Storefront
from subscriptions.models import Subscription

from .emails import send_welcome_email
from .forms import CustomUserCreationForm, ProfileForm
from .models import Profile

import logging

logger = logging.getLogger(__name__)

def register(request):
    """
    Register a new user and create a matching Profile.
    Welcome email failures must never block registration.
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
                # Email issues must not block registration
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
    profile = request.user.profile
    storefront = Storefront.objects.filter(profile=profile).first()

    subscription = (
        Subscription.objects.filter(profile=profile)
        .order_by("-started_at")
        .first()
    )

    context = {
        "profile": profile,
        "storefront": storefront,
        "subscription": subscription,
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def edit_profile(request):
    """Allow the logged-in user to edit their business profile."""
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "business_name": request.user.username,
            "contact_email": getattr(request.user, "email", "") or "",
        },
    )

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your business profile has been updated.")
            return redirect("dashboard")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "accounts/edit_profile.html", {"form": form, "profile": profile})

# Dev-only email preview view

from django.conf import settings
from django.http import HttpResponse

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
    assets = _email_asset_urls(request)

    context = {
        "user_name": "Preview User",
        "year": timezone.now().year,
        "site_root": links.site_root,
        "dashboard_url": links.dashboard_url,
        "about_url": links.about_url,
        "pricing_url": links.pricing_url,
        "faq_url": links.faq_url,
        **assets,
    }

    if kind == "welcome":
        html = render_to_string("emails/welcome.html", context)
        return HttpResponse(html)

    if kind == "subscription":
        html = render_to_string("emails/subscription_confirmed.html", context)
        return HttpResponse(html)

    return HttpResponse("Unknown preview type", status=404)
