# storefronts/models.py
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.conf import settings

from accounts.models import Profile


class Storefront(models.Model):
    """
    Public storefront for a business.

    Linked 1:1 to a Profile. Stores simple page content plus a dedicated logo
    and basic categorisation so we can show it on the Explore page.
    """

    # Core linkage
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name="storefront",
    )

    # Basic content
    headline = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    contact_details = models.TextField(blank=True)

    # Dedicated storefront logo
    logo = models.ImageField(
        upload_to="storefront_logos/",
        blank=True,
        null=True,
        help_text="Brand logo shown at the top of your storefront.",
    )

    # Visibility
    is_active = models.BooleanField(
        default=False,
        help_text="If ticked, this storefront can appear in Explore.",
    )

    # Simple business categorisation for Explore filtering
    BUSINESS_CATEGORY_CHOICES = [
        ("beauty_wellness", "Beauty & wellness"),
        ("food_drink", "Food & drink"),
        ("retail", "Retail & shops"),
        ("events_tickets", "Events & tickets"),
        ("services", "Professional services"),
        ("education", "Courses & education"),
        ("sports_fitness", "Sports & fitness"),
        ("digital_products", "Digital products & subscriptions"),
        ("charity", "Charities & causes"),
        ("other", "Other"),
    ]
    business_category = models.CharField(
        max_length=50,
        blank=True,
        choices=BUSINESS_CATEGORY_CHOICES,
        help_text="Used to group storefronts in Explore.",
    )

    REGION_CHOICES = [
        ("online", "Online / remote"),
        ("uk", "United Kingdom"),
        ("eu", "Europe"),
        ("us", "United States"),
        ("africa", "Africa"),
        ("asia", "Asia"),
        ("oceania", "Oceania / Australia"),
        ("other", "Other / not listed"),
    ]
    region = models.CharField(
        max_length=50,
        blank=True,
        choices=REGION_CHOICES,
        help_text="Where your business mainly operates.",
    )


    slug = models.SlugField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Ensure each storefront has a unique slug based on the headline or username.

        This runs only when slug is empty, so existing slugs are not changed.
        """
        if not self.slug:
            # Base slug from headline, otherwise username, otherwise "storefront"
            base = slugify(self.headline or self.profile.user.username or "storefront")
            if not base:
                base = "storefront"

            candidate = base
            counter = 1
            # Ensure uniqueness
            while Storefront.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{counter}"
                counter += 1

            self.slug = candidate

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("storefront_detail", args=[self.slug])

    def __str__(self):
        return self.headline or f"{self.profile.user.username}'s storefront"


class StorefrontCard(models.Model):
    """
    A manually-linked MintKit card shown on the storefront.

    For now everything is entered by hand; later we can sync with the MintKit app.
    """

    storefront = models.ForeignKey(
        Storefront,
        on_delete=models.CASCADE,
        related_name="cards",
    )

    title = models.CharField(max_length=80)
    price_label = models.CharField(
        max_length=40,
        blank=True,
        help_text="E.g. £25.00 or From £10",
    )
    image_url = models.URLField(
        "Card image URL (thumbnail.webp)",
        max_length=500,
        help_text="Paste the thumbnail.webp URL from MintKit.",
    )
    buy_url = models.URLField(
        "Buy / details URL",
        max_length=500,
        help_text="Link customers should use to buy or view the card.",
    )
    description = models.TextField(
        blank=True,
        help_text="Short description of what the card includes, expiry rules, etc.",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first.",
    )

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.title or f"Card {self.pk}"


class StorefrontLayout(models.Model):
    """
    Store each storefront's editor layout in the DB,
    so it loads the same on any device and for the correct owner.
    """
    storefront = models.OneToOneField(
        "Storefront",
        on_delete=models.CASCADE,
        related_name="layout_data"
    )

    layout = models.JSONField(default=dict, blank=True)   # block positions/sizes
    styles = models.JSONField(default=dict, blank=True)   # per-block typography + hidden
    bg = models.CharField(max_length=20, default="#ffffff", blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Layout for storefront #{self.storefront_id}"
