# accounts/admin.py
from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for business profiles.
    Makes it easy to search / filter business accounts.
    """
    list_display = (
        "business_name",
        "user",
        "contact_email",
        "created_at",
    )
    search_fields = (
        "business_name",
        "user__username",
        "user__email",
        "contact_email",
    )
    list_filter = ("created_at",)
    ordering = ("-created_at",)
