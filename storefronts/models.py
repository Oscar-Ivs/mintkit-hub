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
