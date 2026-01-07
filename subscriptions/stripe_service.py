# subscriptions/stripe_service.py
import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def init_stripe() -> None:
    """Configure Stripe SDK (call from any view that hits Stripe)."""
    secret = (getattr(settings, "STRIPE_SECRET_KEY", "") or "").strip()
    if not secret:
        raise ImproperlyConfigured("Missing required setting: STRIPE_SECRET_KEY")

    stripe.api_key = secret


def _get_setting(name: str) -> str:
    """Fetch a setting safely and trim whitespace."""
    return (getattr(settings, name, "") or "").strip()


def _normalize(plan_code: str, billing: str) -> tuple[str, str]:
    """
    Normalize plan_code and billing.
    Supports legacy plan codes like 'basic_annual' / 'basic_monthly'.
    """
    plan = (plan_code or "").strip().lower()
    bill = (billing or "monthly").strip().lower()

    if plan.endswith("_annual"):
        plan = plan.replace("_annual", "")
        bill = "annual"
    elif plan.endswith("_monthly"):
        plan = plan.replace("_monthly", "")
        bill = "monthly"

    if bill not in ("monthly", "annual"):
        bill = "monthly"

    return plan, bill


def get_stripe_price_id(plan_code: str, billing: str = "monthly") -> str:
    """
    Return the correct Stripe Price ID for the plan and billing cycle.

    Expects these settings (env vars on Heroku):
      - STRIPE_PRICE_BASIC
      - STRIPE_PRICE_BASIC_ANNUAL
      - STRIPE_PRICE_PRO (optional/future)
      - STRIPE_PRICE_PRO_ANNUAL (optional/future)
    """
    plan, bill = _normalize(plan_code, billing)

    if plan == "trial":
        raise ImproperlyConfigured("Trial has no Stripe price id (it should not go through checkout).")

    setting_map = {
        ("basic", "monthly"): "STRIPE_PRICE_BASIC",
        ("basic", "annual"): "STRIPE_PRICE_BASIC_ANNUAL",
        ("pro", "monthly"): "STRIPE_PRICE_PRO",
        ("pro", "annual"): "STRIPE_PRICE_PRO_ANNUAL",
    }

    setting_name = setting_map.get((plan, bill))
    if not setting_name:
        raise ImproperlyConfigured(f"Unknown plan code: {plan}")

    price_id = _get_setting(setting_name)
    if not price_id:
        raise ImproperlyConfigured(
            f"Missing Stripe price id for plan={plan}, billing={bill}. "
            f"Set {setting_name} in settings/env vars."
        )

    return price_id
