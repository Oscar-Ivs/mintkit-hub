from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """
    Ensure a Profile exists for every User.
    - Create a Profile when a User is first created.
    - Optionally update fields if needed on subsequent saves.
    """
    if created:
        Profile.objects.create(
            user=instance,
            contact_email=instance.email or "",
            business_name=instance.username,  # simple default
        )
    else:
        # For now just ensure the profile exists
        Profile.objects.get_or_create(user=instance)
