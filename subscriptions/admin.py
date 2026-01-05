# subscriptions/admin.py
from django.contrib import admin

from .models import MintKitAccess, Subscription, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "stripe_price_id",
        "max_storefronts",
        "max_featured_cards",
        "is_active",
        "sort_order",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "code", "stripe_price_id")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "plan",
        "status",
        "current_period_end",
        "stripe_customer_id",
        "stripe_subscription_id",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "plan")
    search_fields = (
        "profile__user__username",
        "profile__user__email",
        "stripe_customer_id",
        "stripe_subscription_id",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(MintKitAccess)
class MintKitAccessAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "principal_id",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "profile__user__username",
        "profile__user__email",
        "principal_id",
    )
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at")
