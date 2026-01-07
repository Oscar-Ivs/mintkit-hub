# core/tests/test_studio_access.py
from types import SimpleNamespace
from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from core.views import _studio_access


class StudioAccessTests(SimpleTestCase):
    def test_active_subscription_allows_access(self):
        sub = SimpleNamespace(status="active", current_period_end=None)
        self.assertTrue(_studio_access(sub))

    def test_trialing_allows_access_until_end_date(self):
        sub = SimpleNamespace(
            status="trialing",
            current_period_end=timezone.now() + timedelta(days=1),
        )
        self.assertTrue(_studio_access(sub))

    def test_trialing_denies_access_after_end_date(self):
        sub = SimpleNamespace(
            status="trialing",
            current_period_end=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(_studio_access(sub))

    def test_missing_subscription_denies_access(self):
        self.assertFalse(_studio_access(None))

    def test_unknown_status_denies_access(self):
        sub = SimpleNamespace(status="past_due", current_period_end=None)
        self.assertFalse(_studio_access(sub))
