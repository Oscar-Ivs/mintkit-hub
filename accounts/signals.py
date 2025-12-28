from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    # Ensure a Profile exists for every User
    if created:
        Profile.objects.create(
            user=instance,
            contact_email=instance.email or "",
            business_name=instance.username,  # simple default
        )
    else:
        Profile.objects.get_or_create(user=instance)
