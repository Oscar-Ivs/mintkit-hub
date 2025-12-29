from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class StorefrontViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sfuser",
            email="sf@example.com",
            password="TestPass123!",
        )

    def test_explore_page_loads(self):
        # Explore page should load publicly (adjust if it requires login)
        resp = self.client.get("/storefront/explore/")
        self.assertIn(resp.status_code, (200, 302))

    def test_my_storefront_requires_login(self):
        # My storefront should be protected
        resp = self.client.get("/storefront/my/")
        self.assertEqual(resp.status_code, 302)

    def test_my_storefront_loads_when_logged_in(self):
        self.client.login(username="sfuser", password="TestPass123!")
        resp = self.client.get("/storefront/my/")
        self.assertEqual(resp.status_code, 200)
