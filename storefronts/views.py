# storefronts/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
import json
from django.http import JsonResponse

from .forms import StorefrontForm, StorefrontCardFormSet
from .models import Storefront, StorefrontLayout


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

    # Backfill slug if it is missing (older rows or freshly created without slug)
    if not storefront.slug:
        storefront.save()

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
    Public “Explore” page that lists all storefronts which have been
    marked as public.

    Supports:
      - view mode: grid or list (remembered in the session)
      - sorting: featured (default), name, newest (also remembered)
      - basic filtering by business category and region
    """

    # ----- View mode (grid / list), remembered per-session -----
    stored_view = request.session.get("explore_view_mode", "list")
    requested_view = request.GET.get("view")

    if requested_view in ("list", "grid"):
        view_mode = requested_view
        request.session["explore_view_mode"] = view_mode
    else:
        view_mode = stored_view
        if view_mode not in ("list", "grid"):
            view_mode = "list"
            request.session["explore_view_mode"] = view_mode

    # ----- Sort option, remembered per-session -----
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

    # ----- Filters: category & region -----
    category = request.GET.get("category", "all")
    region = request.GET.get("region", "all")

    queryset = Storefront.objects.filter(is_active=True)

    if category != "all" and category:
        queryset = queryset.filter(business_category=category)

    if region != "all" and region:
        queryset = queryset.filter(region=region)

    # Apply ordering
    if sort == "name":
        queryset = queryset.order_by("headline", "id")
        sort_label = "Name A-Z"
    elif sort == "newest":
        queryset = queryset.order_by("-id")
        sort_label = "Newest first"
    else:
        sort = "featured"
        queryset = queryset.order_by("-id")
        sort_label = "Featured"

    storefronts = list(queryset)

    context = {
        "storefronts": storefronts,
        "view_mode": view_mode,
        "sort": sort,
        "sort_label": sort_label,
        "selected_category": category,
        "selected_region": region,
        "category_choices": Storefront.BUSINESS_CATEGORY_CHOICES,
        "region_choices": Storefront.REGION_CHOICES,
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

@login_required
def storefront_layout_load(request, storefront_id):
    """
    Only allow the owner to load their layout.
    """
    storefront = get_object_or_404(Storefront, id=storefront_id, owner=request.user)
    layout_obj, _ = StorefrontLayout.objects.get_or_create(storefront=storefront)

    return JsonResponse({
        "layout": layout_obj.layout or {},
        "styles": layout_obj.styles or {},
        "bg": layout_obj.bg or "#ffffff",
        "updated_at": layout_obj.updated_at.isoformat(),
    })


@login_required
def storefront_layout_save(request, storefront_id):
    """
    Only allow the owner to save their layout.
    Accept JSON and store it in the DB.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    storefront = get_object_or_404(Storefront, id=storefront_id, owner=request.user)
    layout_obj, _ = StorefrontLayout.objects.get_or_create(storefront=storefront)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    layout_obj.layout = payload.get("layout", {}) or {}
    layout_obj.styles = payload.get("styles", {}) or {}
    layout_obj.bg = payload.get("bg", "#ffffff") or "#ffffff"
    layout_obj.save()

    return JsonResponse({"ok": True, "updated_at": layout_obj.updated_at.isoformat()})