from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StorefrontForm, StorefrontCardFormSet
from .models import Storefront


# storefronts/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404

from .forms import StorefrontForm
from .models import Storefront


@login_required
def my_storefront(request):
    """
    Let the logged-in business owner manage their storefront,
    plus up to three manually linked MintKit cards.
    """

    # Ensure the user has a storefront row
    profile = request.user.profile
    storefront, created = Storefront.objects.get_or_create(
        profile=profile,
        defaults={
            "headline": f"{request.user.username}'s storefront",
            "description": "",
            "contact_details": profile.contact_email or "",
            "is_active": False,
        },
    )

    if request.method == "POST":
        form = StorefrontForm(request.POST, request.FILES, instance=storefront)
        card_formset = StorefrontCardFormSet(
            request.POST,
            instance=storefront,
            prefix="cards",
        )

        if form.is_valid() and card_formset.is_valid():
            form.save()
            card_formset.save()
            messages.success(request, "Storefront updated.")
            return redirect("my_storefront")
    else:
        form = StorefrontForm(instance=storefront)
        card_formset = StorefrontCardFormSet(
            instance=storefront,
            prefix="cards",
        )

    has_cards = storefront.cards.exists()

    public_url = request.build_absolute_uri(storefront.get_absolute_url())

    context = {
        "storefront": storefront,
        "form": form,
        "card_formset": card_formset,
        "public_url": public_url,
        "has_cards": has_cards, 
    }
    return render(request, "storefronts/my_storefront.html", context)


def explore_storefronts(request):
    """
    Show only storefronts that chose to be listed publicly.
    """
    storefronts = Storefront.objects.filter(is_active=True).order_by("headline")
    return render(
        request,
        "storefronts/explore_storefronts.html",
        {"storefronts": storefronts},
    )



def storefront_detail(request, slug):
    """
    Public storefront page.

    The page is always available if you have the link.
    The is_active flag is used only for Explore listing, not for the URL itself.
    """
    storefront = get_object_or_404(Storefront, slug=slug)
    return render(
        request,
        "storefronts/storefront_detail.html",
        {"storefront": storefront},
    )
