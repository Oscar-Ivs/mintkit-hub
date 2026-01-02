# accounts/views.py
import logging
from datetime import date, datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from storefronts.models import Storefront
from subscriptions.models import Subscription, MintKitAccess
from subscriptions.forms import MintKitAccessForm

from .emails import send_welcome_email, _brand_links, _email_asset_urls
from .forms import CustomUserCreationForm, ProfileForm, AccountEmailForm
from .models import Profile

logger = logging.getLogger(__name__)


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


def _studio_access_flags(subscription):
    """
    Determine Studio access based on subscription status + trial end date.
    Returns: (studio_access: bool, trial_expired: bool)
    """
    if not subscription:
        return False, False

    status = (getattr(subscription, "status", "") or "").lower()
    today = timezone.localdate()

    if status == "active":
        return True, False

    if status in {"trial", "trialing"}:
        end_date = _to_date(getattr(subscription, "current_period_end", None))

        # If end date missing, keep access (useful for dev/admin testing)
        if end_date is None:
            return True, False

        if end_date < today:
            return False, True

        return True, False

    return False, False


def register(request):
    """Register a new user and create a matching Profile."""
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

    studio_access, trial_expired = _studio_access_flags(subscription)

    # MintKit PID link (one-to-one to profile)
    mintkit_access = MintKitAccess.objects.filter(profile=profile).first()

    def _mask_pid(pid: str) -> str:
        parts = (pid or "").split("-")
        if len(parts) <= 6:
            return pid
        return "-".join(parts[:3]) + "-…" + "-".join(parts[-2:])

    masked_pid = _mask_pid(mintkit_access.principal_id) if mintkit_access else ""
    show_pid_form = False

    # Always render an empty field by default (keeps UI clean and prevents accidental overwrites)
    mintkit_form = MintKitAccessForm()

    if request.method == "POST" and request.POST.get("form_name") == "mintkit_pid":
        show_pid_form = True
        mintkit_form = MintKitAccessForm(request.POST, instance=mintkit_access)

        if mintkit_form.is_valid():
            # If a PID already exists, require explicit confirmation before replacing it
            if mintkit_access and request.POST.get("confirm_replace") != "on":
                mintkit_form.add_error(None, "Tick the confirmation box to replace the currently linked PID.")
            else:
                obj = mintkit_form.save(commit=False)
                obj.profile = profile
                obj.save()

                messages.success(request, "MintKit Principal ID saved.")
                return redirect("dashboard")

    context = {
        "profile": profile,
        "storefront": storefront,
        "subscription": subscription,
        "studio_access": studio_access,
        "trial_expired": trial_expired,
        "mintkit_access": mintkit_access,
        "masked_pid": masked_pid,
        "mintkit_form": mintkit_form,
        "show_pid_form": show_pid_form,
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def edit_profile(request):
    """Allow the logged-in user to edit profile + account email."""
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

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "profile": profile,
            "form": profile_form,  # kept for older templates
            "profile_form": profile_form,
            "email_form": email_form,
        },
    )


def email_preview(request, kind: str):
    """Dev-only email preview in the browser."""
    if not settings.DEBUG:
        return HttpResponse("Not found", status=404)

    links = _brand_links(request)
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
