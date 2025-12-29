from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class AuthFlowTests(TestCase):
    def setUp(self):
        # Create a user for login-required pages
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_dashboard_redirects_when_logged_out(self):
        # Dashboard should be protected
        resp = self.client.get("/accounts/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login", resp["Location"])

    def test_dashboard_loads_when_logged_in(self):
        # Authenticated user should see dashboard
        self.client.login(username="testuser", password="TestPass123!")
        resp = self.client.get("/accounts/dashboard/")
        self.assertEqual(resp.status_code, 200)

    def test_register_page_loads(self):
        # Register page should be reachable
        resp = self.client.get("/accounts/register/")
        self.assertIn(resp.status_code, (200, 302))
