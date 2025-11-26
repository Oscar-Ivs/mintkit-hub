from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    Extends the built-in User with business-related fields for MintKit Hub.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Helpful in admin / shell
        return f"Profile for {self.user.username}"
