# subscriptions/stripe_service.py
import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def init_stripe():
    """
    Configure Stripe SDK once per request path that needs it.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise ImproperlyConfigured("Missing required setting: STRIPE_SECRET_KEY")

    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe_price_id(plan_code: str, billing: str = "monthly") -> str:
    """
    Returns the correct Stripe Price ID for the plan.

    billing:
      - "monthly" (default)
      - "annual"
    """
    if plan_code == "basic":
        if billing == "annual":
            price_id = getattr(settings, "STRIPE_PRICE_BASIC_ANNUAL", "") or ""
        else:
            price_id = settings.STRIPE_PRICE_BASIC

    elif plan_code == "pro":
        # Future support
        price_id = settings.STRIPE_PRICE_PRO

    else:
        raise ImproperlyConfigured(f"Unknown plan code: {plan_code}")

    if not price_id:
        raise ImproperlyConfigured(f"Missing Stripe price id for plan={plan_code}, billing={billing}")

    return price_id
