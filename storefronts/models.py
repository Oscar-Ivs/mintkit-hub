# storefronts/models.py
from django.db import models
from django.urls import reverse

from accounts.models import Profile


class Storefront(models.Model):
    """
    Public storefront for a business.

    Linked 1:1 to a Profile. Stores simple page content plus a dedicated logo.
    """
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name="storefront",
    )
    headline = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    contact_details = models.TextField(blank=True)

    # NEW: dedicated storefront logo
    logo = models.ImageField(
        upload_to="storefront_logos/",
        blank=True,
        null=True,
        help_text="Brand logo shown at the top of your storefront.",
    )

    is_active = models.BooleanField(default=False)
    slug = models.SlugField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        "Storefront",
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

