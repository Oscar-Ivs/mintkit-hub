# subscriptions/stripe_service.py
import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def init_stripe() -> None:
    """
    Configure Stripe SDK once per request path that needs it.
    """
    secret_key = getattr(settings, "STRIPE_SECRET_KEY", "") or ""
    if not secret_key:
        raise ImproperlyConfigured("Missing required setting: STRIPE_SECRET_KEY")

    stripe.api_key = secret_key


def _normalize_plan(plan_code: str) -> str:
    return (plan_code or "").strip().lower()


def _normalize_billing(billing: str) -> str:
    b = (billing or "").strip().lower()

    # Accept common synonyms to avoid brittle query-string issues
    if b in ("", "month", "monthly", "mo"):
        return "monthly"
    if b in ("year", "yearly", "annual", "annually", "yr"):
        return "annual"

    raise ImproperlyConfigured(
        f"Unknown billing value: {billing!r} (expected 'monthly' or 'annual')"
    )


def get_stripe_price_id(plan_code: str, billing: str = "monthly") -> str:
    """
    Returns the correct Stripe Price ID for the plan.

    billing:
      - "monthly" (default)
      - "annual"
    """
    plan = _normalize_plan(plan_code)
    cycle = _normalize_billing(billing)

    # Map (plan, billing) -> Django settings attribute name
    setting_map = {
        ("basic", "monthly"): "STRIPE_PRICE_BASIC",
        ("basic", "annual"): "STRIPE_PRICE_BASIC_ANNUAL",

        # Pro can be added later (safe to keep mappings now)
        ("pro", "monthly"): "STRIPE_PRICE_PRO",
        ("pro", "annual"): "STRIPE_PRICE_PRO_ANNUAL",
    }

    setting_name = setting_map.get((plan, cycle))
    if not setting_name:
        raise ImproperlyConfigured(
            f"Unknown plan/billing combination: plan={plan!r}, billing={cycle!r}"
        )

    price_id = getattr(settings, setting_name, "") or ""
    if not price_id:
        raise ImproperlyConfigured(
            f"Missing Stripe price id for plan={plan}, billing={cycle}. "
            f"Expected setting/env var: {setting_name}"
        )

    return price_id
