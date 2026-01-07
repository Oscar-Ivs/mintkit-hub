# subscriptions/stripe_service.py
import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def init_stripe() -> None:
    """
    Configure Stripe SDK for calls in views/services that touch Stripe.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise ImproperlyConfigured("Missing required setting: STRIPE_SECRET_KEY")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe_price_id(plan_code: str, billing: str = "monthly") -> str:
    """
    Return the correct Stripe Price ID for a plan + billing cadence.

    plan_code:
      - "basic"
      - "pro" (future)

    billing:
      - "monthly" (default)
      - "annual"
    """
    billing = (billing or "monthly").strip().lower()

    if plan_code == "basic":
        if billing == "annual":
            price_id = getattr(settings, "STRIPE_PRICE_BASIC_ANNUAL", "") or ""
        else:
            price_id = getattr(settings, "STRIPE_PRICE_BASIC", "") or ""

    elif plan_code == "pro":
        # Future support: add STRIPE_PRICE_PRO_ANNUAL later when needed
        price_id = getattr(settings, "STRIPE_PRICE_PRO", "") or ""

    else:
        raise ImproperlyConfigured(f"Unknown plan code: {plan_code}")

    if not price_id:
        raise ImproperlyConfigured(
            f"Missing Stripe price id for plan={plan_code}, billing={billing}"
        )

    return price_id
