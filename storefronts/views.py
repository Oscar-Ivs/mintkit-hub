from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StorefrontForm
from .models import Storefront


@login_required
def my_storefront(request):
    """
    Let the logged-in business owner preview and edit *their* storefront.

    We link the storefront to request.user.profile (not a field called 'owner').
    If a storefront does not exist yet, we create one on the fly and then
    display the edit form + preview.
    """

    # Every user should have a Profile because of the signal, but be defensive:
    profile = getattr(request.user, "profile", None)
    if profile is None:
        # Fallback – you can redirect to a “complete your profile” page if you like
        messages.error(request, "Please complete your profile before editing a storefront.")
        return redirect("dashboard")

    # Fetch existing storefront for this profile or create a new one
    storefront, created = Storefront.objects.get_or_create(
        profile=profile,
        defaults={
            "headline": profile.business_name or f"{request.user.username}'s storefront",
            "description": "",
            "contact_details": profile.contact_email or "",
            "is_active": False,
        },
    )

    if request.method == "POST":
        form = StorefrontForm(request.POST, instance=storefront)
        if form.is_valid():
            form.save()
            messages.success(request, "Storefront details updated.")
            return redirect("my_storefront")
    else:
        form = StorefrontForm(instance=storefront)

    # Build the full public URL once here, not in the template
    public_url = request.build_absolute_uri(storefront.get_absolute_url())

    context = {
        "storefront": storefront,
        "form": form,
        "public_url": public_url,
    }
    return render(request, "storefronts/my_storefront.html", context)


def explore_storefronts(request):
    """
    Public list of storefronts that have been marked as active/public.
    Used by the Explore page.
    """
    storefronts = (
        Storefront.objects.filter(is_active=True)
        .select_related("profile")
        .order_by("headline")
    )

    return render(
        request,
        "storefronts/explore_storefronts.html",
        {"storefronts": storefronts},
    )


def storefront_detail(request, slug):
    """
    Public view of a single storefront, used for the public URL
    /storefront/<slug>/.
    """
    storefront = get_object_or_404(Storefront, slug=slug, is_active=True)

    return render(
        request,
        "storefronts/storefront_detail.html",
        {"storefront": storefront},
    )
