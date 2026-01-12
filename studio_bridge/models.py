import uuid
from django.db import models

class CardLink(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nft_id = models.CharField(max_length=128)
    open_url = models.URLField(max_length=800)
    image_url = models.URLField(max_length=800, blank=True)
    recipient_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.token} ({self.nft_id})"
