import tempfile
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

User = get_user_model()


@override_settings(
    MEDIA_ROOT=tempfile.gettempdir(),
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class MediaUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mediauser",
            email="media@example.com",
            password="TestPass123!",
        )

    def test_upload_logo_does_not_crash(self):
        self.client.login(username="mediauser", password="TestPass123!")

        # Minimal valid image-like payload (content doesn't need to be a real PNG for storage test)
        fake_file = SimpleUploadedFile(
            "logo.png",
            b"fake-image-bytes",
            content_type="image/png",
        )

        # Adjust the POST URL and field name to match your form/view
        resp = self.client.post("/storefront/my/", {"logo": fake_file}, follow=True)

        # The key check: request completes and doesn't 500
        self.assertNotEqual(resp.status_code, 500)
