from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

from subscriptions.models import Subscription
from storefronts.models import Storefront

from .emails import send_welcome_email
from .models import Profile
from .forms import ProfileForm


def register(request):
    """
    Simple registration view using Django's built-in UserCreationForm.
    Also creates a matching Profile for the new user.
    """
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Make sure this user has a Profile; avoid duplicates with get_or_create
            Profile.objects.get_or_create(
                user=user,
                defaults={
                    "business_name": user.username,
                    "contact_email": getattr(user, "email", "") or "",
                },
            )

            # Send welcome email if the user has an email address
            send_welcome_email(user, request=request)

            messages.success(
                request,
                "Your account has been created. You can now log in."
            )
            return redirect("login")
    else:
        form = UserCreationForm()

    context = {"form": form}
    return render(request, "accounts/register.html", context)


def logout_view(request):
    """
    Log the user out and redirect to the homepage.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def dashboard(request):
    """
    Main control panel for the logged-in user.

    Shows:
    - Business profile info
    - Current storefront status
    - Current subscription / trial info
    """
    profile = request.user.profile
    storefront = Storefront.objects.filter(profile=profile).first()

    # Get the most recent subscription for this profile (if any)
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
    """
    Allow the logged-in user to edit their business profile.
    """
    # Make sure there is a Profile (extra safety)
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

    context = {
        "form": form,
        "profile": profile,
    }
    return render(request, "accounts/edit_profile.html", context)
