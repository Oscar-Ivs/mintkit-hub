# subscriptions/stripe_service.py
from __future__ import annotations

from dataclasses import dataclass
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _get_setting(name: str) -> str:
    val = getattr(settings, name, "") or ""
    if not val:
        raise ImproperlyConfigured(f"Missing required setting: {name}")
    return val


def get_stripe_price_id(plan_code: str, fallback_price_id: str = "") -> str:
    """
    Resolve Stripe Price ID.
    Priority:
      1) Plan.stripe_price_id (passed in as fallback_price_id if present)
      2) Environment settings STRIPE_PRICE_BASIC / STRIPE_PRICE_PRO
    """
    if fallback_price_id:
        return fallback_price_id

    code = (plan_code or "").lower().strip()
    if code == "basic":
        return _get_setting("STRIPE_PRICE_BASIC")
    if code == "pro":
        return _get_setting("STRIPE_PRICE_PRO")

    raise ImproperlyConfigured(
        f"No Stripe Price ID configured for plan code '{plan_code}'. "
        "Set plan.stripe_price_id in admin or add STRIPE_PRICE_BASIC/PRO env vars."
    )


def init_stripe():
    """
    Stripe API key is pulled from Django settings (env vars on Heroku).
    """
    import stripe  # local import keeps startup errors obvious
    stripe.api_key = _get_setting("STRIPE_SECRET_KEY")
    return stripe


def site_url() -> str:
    """
    Used to build absolute return URLs. SITE_URL should be like: https://mintkit.co.uk
    """
    return (_get_setting("SITE_URL")).rstrip("/")
