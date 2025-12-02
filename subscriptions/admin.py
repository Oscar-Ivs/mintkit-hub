# subscriptions/admin.py
from django.contrib import admin
from .models import SubscriptionPlan, Subscription, MintKitAccess


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "monthly_price", "is_active", "max_total_cards")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "monthly_price")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("profile", "plan", "status", "started_at", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = ("profile__user__username", "profile__business_name")
    autocomplete_fields = ("profile", "plan")


@admin.register(MintKitAccess)
class MintKitAccessAdmin(admin.ModelAdmin):
    list_display = ("profile", "principal_id", "linked_at", "last_seen_at")
    search_fields = ("principal_id", "profile__user__username", "profile__business_name")
    autocomplete_fields = ("profile",)
