# subscriptions/models.py
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """
    Local representation of subscription tiers.

    Stripe remains the source of truth for billing, but plans in the DB help keep
    UI stable and provide feature limits for grading/demo clarity.
    """

    code = models.SlugField(
        unique=True,
        help_text="Short unique code used in URLs and logic (e.g. basic, pro).",
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    # Stripe Price ID for this plan (e.g. price_123...)
    stripe_price_id = models.CharField(max_length=120, blank=True)

    # Display price for UI/admin convenience (Stripe remains the billing source of truth)
    monthly_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Monthly price shown in the UI/admin (e.g. 9.99).",
    )

    # Optional feature limits for grading/demo clarity
    max_storefronts = models.PositiveIntegerField(default=1)
    max_featured_cards = models.PositiveIntegerField(default=3)

    # Optional overall cap (helps admin/UX messaging; not strictly enforced unless coded)
    max_total_cards = models.PositiveIntegerField(
        default=0,
        help_text="0 = unlimited (unless enforced elsewhere).",
    )

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "monthly_price", "name"]

    def __str__(self) -> str:
        return self.name


class Subscription(models.Model):
    """
    Tracks a user's subscription state inside Django.

    Billing is handled by Stripe; this model stores current status and Stripe IDs
    used to sync via webhooks.
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

    # Used by pricing/admin in some places; keep it to avoid FieldError
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscription first started (set when first activated/trialed).",
    )

    current_period_end = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Auto-populate started_at the first time a subscription becomes active/trialing
        if self.started_at is None and self.status in {self.STATUS_ACTIVE, self.STATUS_TRIALING}:
            self.started_at = timezone.now()
        super().save(*args, **kwargs)

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

    # Admin/UI often expects these fields
    linked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the Principal ID was first linked.",
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the Studio link was used/confirmed (optional).",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this mapping was first created.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # If principal_id is added for the first time, stamp linked_at
        if self.principal_id and self.linked_at is None:
            self.linked_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.profile} ↔ {self.principal_id}"
