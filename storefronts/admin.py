# storefronts/admin.py
from django.contrib import admin
from .models import Storefront


@admin.register(Storefront)
class StorefrontAdmin(admin.ModelAdmin):
    """
    Admin configuration for storefronts.
    Lets you quickly see which storefronts are live.
    """
    list_display = (
        "profile",
        "slug",
        "headline",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = (
        "slug",
        "headline",
        "profile__business_name",
        "profile__user__username",
    )
    ordering = ("-created_at",)
    prepopulated_fields = {
        "slug": ("headline",),  # only affects admin form; save() still handles empty slug
    }
