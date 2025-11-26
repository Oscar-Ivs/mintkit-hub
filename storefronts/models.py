from django.db import models
from django.utils.text import slugify

from accounts.models import Profile


class Storefront(models.Model):
    """
    A public storefront page for a business.
    One storefront per Profile for this project.
    """
    owner = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name='storefront'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    headline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not provided
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            # Ensure slug is unique
            while Storefront.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"

            self.slug = slug

        super().save(*args, **kwargs)

    def get_public_url_path(self):
        """
        Convenience helper for templates.
        """
        return f"/storefront/{self.slug}/"
