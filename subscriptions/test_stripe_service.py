# subscriptions/tests/test_stripe_service.py
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from subscriptions.stripe_service import get_stripe_price_id, _normalize_billing


class StripeServiceBillingTests(SimpleTestCase):
    def test_normalize_billing_monthly_synonyms(self):
        for value in ("", "month", "monthly", "mo", " Mo "):
            self.assertEqual(_normalize_billing(value), "monthly")

    def test_normalize_billing_annual_synonyms(self):
        for value in ("year", "yearly", "annual", "annually", "yr", " Year "):
            self.assertEqual(_normalize_billing(value), "annual")

    def test_normalize_billing_invalid_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            _normalize_billing("weekly")

    @override_settings(
        STRIPE_PRICE_BASIC="price_basic_monthly_123",
        STRIPE_PRICE_BASIC_ANNUAL="price_basic_annual_456",
    )
    def test_get_stripe_price_id_basic_monthly_and_annual(self):
        # Monthly is default
        self.assertEqual(get_stripe_price_id("basic"), "price_basic_monthly_123")

        # Annual via billing
        self.assertEqual(get_stripe_price_id("basic", "annual"), "price_basic_annual_456")

        # Accept common synonyms
        self.assertEqual(get_stripe_price_id("basic", "yearly"), "price_basic_annual_456")
        self.assertEqual(get_stripe_price_id("basic", "mo"), "price_basic_monthly_123")

    @override_settings(
        STRIPE_PRICE_BASIC="",
        STRIPE_PRICE_BASIC_ANNUAL="price_basic_annual_456",
    )
    def test_missing_monthly_price_setting_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            get_stripe_price_id("basic", "monthly")

    @override_settings(
        STRIPE_PRICE_BASIC="price_basic_monthly_123",
        STRIPE_PRICE_BASIC_ANNUAL="",
    )
    def test_missing_annual_price_setting_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            get_stripe_price_id("basic", "annual")
