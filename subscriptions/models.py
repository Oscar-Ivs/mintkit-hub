# subscriptions/models.py
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """
    Defines a subscription tier, e.g. Trial, Basic, Pro.

    For this project we will keep it simple and mostly configure plans
    via the Django admin rather than doing a full Stripe integration.
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Internal code, e.g. 'trial', 'basic', 'pro'."
    )
    name = models.CharField(
        max_length=50,
        help_text="Human friendly name shown to users."
    )
    description = models.TextField(blank=True)

    # For CI and documentation: simple fixed monthly price in GBP
    monthly_price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Monthly price in GBP (for display / docs)."
    )

    # Soft limits for cards/batches (not enforced in code yet)
    max_batches = models.PositiveIntegerField(
        default=0,
        help_text="Recommended maximum number of batches for this plan."
    )
    max_cards_per_batch = models.PositiveIntegerField(
        default=0,
        help_text="Recommended maximum cards per batch."
    )
    max_total_cards = models.PositiveIntegerField(
        default=0,
        help_text="Recommended total cards across all batches."
    )

    # Stripe integration placeholders (optional for this project)
    stripe_price_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional Stripe Price ID for this plan."
    )

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls order in admin / pricing list."
    )

    class Meta:
        ordering = ["sort_order", "monthly_price", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
    

class Subscription(models.Model):
    """
    Connects a Profile to a SubscriptionPlan and tracks high-level status.

    This is intentionally light: enough for dashboard + docs, without
    locking you into a specific Stripe flow yet.
    """
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_TRIAL, "Trial"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
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
        default=STATUS_TRIAL,
    )

    # Dates
    started_at = models.DateTimeField(auto_now_add=True)
    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End of trial or current paid period."
    )

    # Optional Stripe IDs (stubbed for later)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.profile} → {self.plan} ({self.status})"

    @property
    def is_active(self) -> bool:
        """
        Convenience helper:
        - 'active' or 'trial' and not past current_period_end (if set)
        """
        if self.status not in {self.STATUS_TRIAL, self.STATUS_ACTIVE}:
            return False

        if self.current_period_end:
            return timezone.now() <= self.current_period_end

        return True


class MintKitAccess(models.Model):
    """
    Simple mapping between a Profile and the external MintKit app.

    Stores the Internet Identity principal ID (or any external ID)
    so that later the app can say: 'this Django profile corresponds
    to this MintKit Studio principal'.
    """
    profile = models.OneToOneField(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="mintkit_access",
    )
    principal_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Internet Identity principal (or external MintKit ID)."
    )
    linked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this mapping was first created."
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this principal accessed MintKit via the Hub."
    )

    class Meta:
        verbose_name = "MintKit access link"
        verbose_name_plural = "MintKit access links"

    def __str__(self) -> str:
        return f"{self.profile} ↔ {self.principal_id}"
