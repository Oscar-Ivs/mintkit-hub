# subscriptions/models.py
from django.db import models


class SubscriptionPlan(models.Model):
    """
    Local representation of subscription tiers.

    Stripe is still the source of truth for billing, but having plans in the DB
    makes it easier to show tier info, feature limits, and keep the UI stable.
    """

    code = models.SlugField(
        unique=True,
        help_text="Short unique code used in URLs and logic (e.g. basic, pro).",
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    # Stripe Price ID for this plan (e.g. price_123...)
    stripe_price_id = models.CharField(max_length=120, blank=True)

    # Optional feature limits for grading/demo clarity
    max_storefronts = models.PositiveIntegerField(default=1)
    max_featured_cards = models.PositiveIntegerField(default=3)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class Subscription(models.Model):
    """
    Tracks a user's subscription state inside Django.

    Billing is handled by Stripe; this model stores the current status and the
    Stripe IDs needed to sync via webhooks.
    """

    STATUS_ACTIVE = "active"
    STATUS_TRIALING = "trialing"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELED = "canceled"
    STATUS_INCOMPLETE = "incomplete"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_TRIALING, "Trialing"),
        (STATUS_PAST_DUE, "Past due"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_INCOMPLETE, "Incomplete"),
    ]

    profile = models.ForeignKey(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INCOMPLETE,
    )

    stripe_customer_id = models.CharField(max_length=120, blank=True)
    stripe_subscription_id = models.CharField(max_length=120, blank=True)

    current_period_end = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.profile} → {self.plan} ({self.status})"


class MintKitAccess(models.Model):
    """
    Stores the ICP Principal ID for linking a Hub user to the Studio app.
    """

    profile = models.OneToOneField(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="mintkit_access",
    )
    principal_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Internet Identity Principal ID from MintKit Studio.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this mapping was first created.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.profile} ↔ {self.principal_id}"
