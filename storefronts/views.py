# storefronts/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StorefrontForm
from .models import Storefront
from django.shortcuts import render


@login_required
def my_storefront(request):
    """
    Let the logged-in business owner create or edit *their* storefront.

    We link the storefront to request.user.profile (not a field called 'owner').
    If a storefront doesn't exist yet, we create one on the fly and then show
    the edit form.
    """
    # Every user should have a Profile because of the signal, but be defensive:
    profile = request.user.profile

    # Fetch existing storefront for this profile or create a new one
    storefront, created = Storefront.objects.get_or_create(
        profile=profile,
        defaults={
            "headline": profile.business_name
            or f"{request.user.username}'s storefront",
            "description": "",
            "contact_details": profile.contact_email or "",
            "is_active": False,
        },
    )

    if request.method == "POST":
        form = StorefrontForm(request.POST, instance=storefront)
        if form.is_valid():
            # Keep the link to this profile enforced
            sf = form.save(commit=False)
            sf.profile = profile
            sf.save()
            messages.success(request, "Your storefront has been saved.")
            return redirect("my_storefront")  # URL name used in dashboard link
    else:
        form = StorefrontForm(instance=storefront)

    context = {
        "storefront": storefront,
        "form": form,
        "created": created,  # can be used in template to show 'first time' message
    }
    return render(request, "storefronts/my_storefront.html", context)


def storefront_detail(request, slug):
    """
    Public storefront page. Only show storefronts that are marked active.
    """
    storefront = get_object_or_404(
        Storefront,
        slug=slug,
        is_active=True,
    )
    return render(
        request,
        "storefronts/storefront_detail.html",
        {"storefront": storefront},
    )


def explore_storefronts(request):
    """
    Public list of active storefronts.
    Similar idea to BookBase Community: shows all public storefronts.
    """
    storefronts = (
        Storefront.objects
        .filter(is_active=True)
        .select_related("profile__user")
        .order_by("headline")
    )

    context = {
        "storefronts": storefronts,
    }
    return render(request, "storefronts/explore_storefronts.html", context)