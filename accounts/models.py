# accounts/models.py
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


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


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    """
    Ensure every User always has a Profile:
    - When a User is created, create a matching Profile.
    - On update, just save the existing Profile if it exists.
    """
    if created:
        Profile.objects.create(
            user=instance,
            business_name=instance.username,  # simple default, editable later
            contact_email=getattr(instance, "email", "") or "",
        )
    else:
        # If a profile exists, save it (no-op in most cases, safe to call).
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            # In case a user was created before this signal existed
            Profile.objects.create(
                user=instance,
                business_name=instance.username,
                contact_email=getattr(instance, "email", "") or "",
            )
