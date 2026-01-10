# storefronts/views.py

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator


from .forms import StorefrontForm, StorefrontCardFormSet
from .models import Storefront, StorefrontCard, StorefrontLayout


@login_required
def my_storefront(request):
    """
    Owner dashboard page:
    - edit storefront fields
    - manage cards
    - layout editor overlay saves via JSON endpoints
    """
    profile = request.user.profile

    # Ensure the user has a storefront row
    storefront, _ = Storefront.objects.get_or_create(
        profile=profile,
        defaults={
            "headline": f"{request.user.username}'s storefront",
            "description": "",
            "contact_details": getattr(profile, "contact_email", "") or "",
            "is_active": False,
        },
    )

    # Ensure slug exists (older rows or edge cases)
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

        messages.error(request, "Please correct the errors below before saving your storefront.")
    else:
        form = StorefrontForm(instance=storefront)
        card_formset = StorefrontCardFormSet(instance=storefront, prefix="cards")

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
    Public “Explore” page that lists storefronts marked as public.

    Supports:
    - view mode: grid or list (remembered in the session)
    - sorting: featured (default), name, newest (also remembered)
    - filtering by business category and region
    """
    # View mode (grid / list), remembered per-session
    stored_view = request.session.get("explore_view_mode", "list")
    requested_view = request.GET.get("view")

    if requested_view in ("list", "grid"):
        view_mode = requested_view
        request.session["explore_view_mode"] = view_mode
    else:
        view_mode = stored_view if stored_view in ("list", "grid") else "list"
        request.session["explore_view_mode"] = view_mode

    # Sort option, remembered per-session
    stored_sort = request.session.get("explore_sort", "featured")
    requested_sort = request.GET.get("sort")

    if requested_sort in ("featured", "name", "newest"):
        sort = requested_sort
        request.session["explore_sort"] = sort
    else:
        sort = stored_sort if stored_sort in ("featured", "name", "newest") else "featured"
        request.session["explore_sort"] = sort

    # Filters: category & region
    category = request.GET.get("category", "all")
    region = request.GET.get("region", "all")

    queryset = Storefront.objects.filter(is_active=True).select_related("profile")

    if category != "all" and category:
        queryset = queryset.filter(business_category=category)

    if region != "all" and region:
        queryset = queryset.filter(region=region)

    # Apply ordering + label
    if sort == "name":
        queryset = queryset.order_by("headline", "id")
        sort_label = "Name A-Z"
    elif sort == "newest":
        queryset = queryset.order_by("-created_at", "-id")
        sort_label = "Newest first"
    else:
        # “featured” fallback (kept simple)
        queryset = queryset.order_by("-created_at", "-id")
        sort_label = "Featured"

    # Pagination
    per_page = 10 if view_mode == "list" else 8  # tweak numbers anytime
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    context = {
        "storefronts": list(page_obj.object_list),
        "page_obj": page_obj,
        "total_count": paginator.count,

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

    The is_active flag controls Explore listing only.
    The direct URL remains accessible if the link is known.
    """
    storefront = get_object_or_404(Storefront, slug=slug)
    has_cards = storefront.cards.exists()

    # Always use the same source as the editor endpoints
    layout_obj, _ = StorefrontLayout.objects.get_or_create(storefront=storefront)

    layout = layout_obj.layout or {}
    styles = layout_obj.styles or {}
    bg = layout_obj.bg or "#ffffff"

    # Provide BOTH shapes so template/JS versions don’t drift again:
    # - layout_data payload for JS: { layout, styles, bg }
    # - separate keys in case the template uses them directly
    layout_payload = {"layout": layout, "styles": styles, "bg": bg}

    context = {
        "storefront": storefront,
        "has_cards": has_cards,
        "layout_data": layout_payload,
        "layout": layout,
        "styles": styles,
        "bg": bg,
    }
    return render(request, "storefronts/storefront_detail.html", context)


def _get_owned_storefront_or_404(request, storefront_id):
    """
    Helper: ensure the storefront belongs to the logged-in user.
    """
    return get_object_or_404(
        Storefront,
        id=storefront_id,
        profile=request.user.profile,
    )


@login_required
@require_http_methods(["GET"])
def storefront_layout_load(request, storefront_id):
    """
    GET JSON: load saved layout/styles/bg for the owner's editor.
    """
    storefront = _get_owned_storefront_or_404(request, storefront_id)
    layout_obj, _ = StorefrontLayout.objects.get_or_create(storefront=storefront)

    return JsonResponse(
        {
            "layout": layout_obj.layout or {},
            "styles": layout_obj.styles or {},
            "bg": layout_obj.bg or "#ffffff",
            "updated_at": layout_obj.updated_at.isoformat() if layout_obj.updated_at else None,
        }
    )


@login_required
@require_http_methods(["POST"])
def storefront_layout_save(request, storefront_id):
    """
    POST JSON: save layout/styles/bg from the owner's editor.

    Expected JSON body:
      { "layout": {...}, "styles": {...}, "bg": "#ffffff" }
    """
    storefront = _get_owned_storefront_or_404(request, storefront_id)
    layout_obj, _ = StorefrontLayout.objects.get_or_create(storefront=storefront)

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    layout = payload.get("layout", {})
    styles = payload.get("styles", {})
    bg = payload.get("bg", "#ffffff")

    if not isinstance(layout, dict) or not isinstance(styles, dict) or not isinstance(bg, str):
        return JsonResponse({"ok": False, "error": "Invalid payload types"}, status=400)

    layout_obj.layout = layout or {}
    layout_obj.styles = styles or {}
    layout_obj.bg = bg or "#ffffff"
    layout_obj.save()

    return JsonResponse({"ok": True})

def storefront_card_detail(request, slug, card_id):
    """
    Public “card details” page (Option B).

    Shows a single featured card (image + title + price + description),
    with a Buy/Details button that links to the creator’s external URL.
    """
    storefront = get_object_or_404(Storefront, slug=slug)

    # Ensure the card belongs to this storefront
    card = get_object_or_404(StorefrontCard, storefront=storefront, id=card_id)

    context = {
        "storefront": storefront,
        "card": card,
    }
    return render(request, "storefronts/storefront_card_detail.html", context)
