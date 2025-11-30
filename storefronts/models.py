# storefronts/models.py
from django.db import models
from django.utils.text import slugify

from accounts.models import Profile


class Storefront(models.Model):
    """
    Public-facing storefront for a business.
    One Storefront per Profile for this MVP.
    """
    profile = models.OneToOneField(
    Profile,
    on_delete=models.CASCADE,
    related_name="storefront",
    null=True,       # allow NULL in the DB for this migration
    blank=True,      # allow empty in forms (we still set it in code)
    help_text="The business profile that owns this storefront.",
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Used in the public URL, e.g. /storefront/<slug>/",
    )
    headline = models.CharField(
        max_length=255,
        help_text="Short headline shown at the top of the storefront page.",
    )
    description = models.TextField(
        blank=True,
        help_text="Longer description of the business, services, etc.",
    )
    contact_details = models.TextField(
        blank=True,
        help_text="How customers can contact the business (phone, email, links).",
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Only active storefronts are publicly visible.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this storefront was first created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this storefront was last updated.",
    )

    class Meta:
        verbose_name = "Storefront"
        verbose_name_plural = "Storefronts"

    def __str__(self) -> str:
        # Display something useful in admin & shell
        return self.headline or f"Storefront for {self.profile.business_name}"

    def save(self, *args, **kwargs):
        """
        Auto-generate a slug the first time if none is provided.
        Uses business_name or headline as a base.
        """
        if not self.slug:
            base = self.profile.business_name or self.headline
            self.slug = slugify(base)[:100]  # enforce max length
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """
        Convenience method for templates.
        We'll create 'storefront_detail' URL later.
        """
        from django.urls import reverse
        return reverse("storefront_detail", args=[self.slug])
