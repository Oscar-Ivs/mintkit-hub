# storefronts/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StorefrontForm, StorefrontCardFormSet
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
            prefix="cards",  # keep prefix stable between GET and POST
        )

        if form.is_valid() and card_formset.is_valid():
            form.save()
            card_formset.save()  # <- this actually creates/updates the cards
            messages.success(request, "Storefront updated.")
            return redirect("my_storefront")
        else:
            # Light message so you know *why* nothing changed
            messages.error(
                request,
                "Please correct the errors below before saving your storefront.",
            )
    else:
        form = StorefrontForm(instance=storefront)
        card_formset = StorefrontCardFormSet(
            instance=storefront,
            prefix="cards",
        )

    # Used in the left-hand preview: show card section only if any exist
    has_cards = storefront.cards.exists()

    # Full public URL, shown under the preview
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
    Public “Explore” page that lists all storefronts which have been
    marked as public.

    Supports:
      - view mode: grid or list (remembered in the session)
      - sorting: featured (default), name, newest (also remembered)
    """

    # ----- View mode (grid / list), remembered per-session -----
    stored_view = request.session.get("explore_view_mode", "list")
    requested_view = request.GET.get("view")

    if requested_view in ("list", "grid"):
        view_mode = requested_view
        request.session["explore_view_mode"] = view_mode
    else:
        view_mode = stored_view
        # normalise junk values in the session if any
        if view_mode not in ("list", "grid"):
            view_mode = "list"
            request.session["explore_view_mode"] = view_mode

    # ----- Sort option, also remembered per-session -----
    stored_sort = request.session.get("explore_sort", "featured")
    requested_sort = request.GET.get("sort")

    if requested_sort in ("featured", "name", "newest"):
        sort = requested_sort
        request.session["explore_sort"] = sort
    else:
        sort = stored_sort
        if sort not in ("featured", "name", "newest"):
            sort = "featured"
            request.session["explore_sort"] = sort

    # Only storefronts that are marked as active/public
    queryset = Storefront.objects.filter(is_active=True)

    # Apply ordering based on `sort`
    if sort == "name":
        queryset = queryset.order_by("headline", "id")
        sort_label = "Name A-Z"
    elif sort == "newest":
        queryset = queryset.order_by("-id")
        sort_label = "Newest first"
    else:
        # “Featured” – currently same as newest, but easy to change later
        sort = "featured"
        queryset = queryset.order_by("-id")
        sort_label = "Featured"

    storefronts = list(queryset)

    context = {
        "storefronts": storefronts,
        "view_mode": view_mode,
        "sort": sort,
        "sort_label": sort_label,
    }
    return render(request, "storefronts/explore_storefronts.html", context)


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
