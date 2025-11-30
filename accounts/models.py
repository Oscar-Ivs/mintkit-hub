# accounts/models.py
from django.conf import settings
from django.db import models


class Profile(models.Model):
    """
    Extends the built-in User model with business-specific details.
    One Profile per User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    business_name = models.CharField(
        max_length=255,
        help_text="Public name of the business shown on the storefront.",
    )
    contact_email = models.EmailField(
        help_text="Primary contact email for this business."
    )
    logo = models.ImageField(
        upload_to="logos/",
        blank=True,
        null=True,
        help_text="Optional logo used on dashboard / storefront.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this profile was first created.",
    )

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self) -> str:
        # Helpful string representation in admin & shell
        return self.business_name or f"Profile for {self.user.username}"
