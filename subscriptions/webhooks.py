import logging
import stripe

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse, NoReverseMatch

from .models import Subscription, SubscriptionPlan
from accounts.models import Profile

logger = logging.getLogger(__name__)


def _build_url(url_name: str, fallback_path: str = "/") -> str:
    try:
        path = reverse(url_name)
    except NoReverseMatch:
        path = fallback_path
    return f"{settings.SITE_URL}{path}"


def _profile_email(profile: Profile) -> str | None:
    # Prefer the business contact email, fallback to user email
    email = getattr(profile, "contact_email", "") or ""
    if email:
        return email
    user = getattr(profile, "user", None)
    if user and getattr(user, "email", ""):
        return user.email
    return None


def _profile_name(profile: Profile) -> str:
    user = getattr(profile, "user", None)
    if user:
        return (getattr(user, "first_name", "") or "").strip() or getattr(user, "username", "there")
    return "there"


def _send_html_email(to_email: str, subject: str, template_name: str, context: dict) -> None:
    html = render_to_string(template_name, context)
    text = strip_tags(html)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@mintkit.co.uk",
        to=[to_email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


def _to_dt(unix_ts):
    if not unix_ts:
        return None
    return timezone.datetime.fromtimestamp(unix_ts, tz=timezone.get_current_timezone())


def _update_subscription_from_stripe(stripe_sub: dict, profile: Profile) -> Subscription:
    stripe_price = (stripe_sub.get("items", {})
                          .get("data", [{}])[0]
                          .get("price", {}))

    stripe_price_id = stripe_price.get("id")
    if not stripe_price_id:
        raise ValueError("Stripe subscription missing price id")

    plan = SubscriptionPlan.objects.get(stripe_price_id=stripe_price_id)

    stripe_status = stripe_sub.get("status", "")
    status_map = {
        "trialing": Subscription.STATUS_TRIALING,
        "active": Subscription.STATUS_ACTIVE,
        "past_due": Subscription.STATUS_PAST_DUE,
        "canceled": Subscription.STATUS_CANCELED,
        "incomplete": Subscription.STATUS_INCOMPLETE,
        "unpaid": Subscription.STATUS_UNPAID,
    }
    local_status = status_map.get(stripe_status, Subscription.STATUS_INCOMPLETE)

    sub_id = stripe_sub.get("id")
    period_end = _to_dt(stripe_sub.get("current_period_end"))
    cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
    cancel_at = _to_dt(stripe_sub.get("cancel_at"))

    sub, created = Subscription.objects.get_or_create(
        profile=profile,
        stripe_subscription_id=sub_id,
        defaults={
            "plan": plan,
            "status": local_status,
            "current_period_end": period_end,
            "cancel_at_period_end": cancel_at_period_end,
            "cancel_at": cancel_at,
        }
    )

    if not created:
        sub.plan = plan
        sub.status = local_status
        sub.current_period_end = period_end
        sub.cancel_at_period_end = cancel_at_period_end
        sub.cancel_at = cancel_at
        sub.save(update_fields=[
            "plan", "status", "current_period_end",
            "cancel_at_period_end", "cancel_at", "updated_at"
        ])

    # If a paid subscription becomes active, mark any trial as ended (so trial is "used")
    if local_status == Subscription.STATUS_ACTIVE:
        Subscription.objects.filter(
            profile=profile,
            plan__code="trial",
            status=Subscription.STATUS_TRIALING,
        ).update(status=Subscription.STATUS_CANCELED, current_period_end=timezone.now())

    return sub


@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})

    try:
        # 1) Checkout complete → subscription confirmed
        if event_type == "checkout.session.completed":
            session = data_object
            sub_id = session.get("subscription")
            customer_id = session.get("customer")

            if not (sub_id and customer_id):
                return HttpResponse(status=200)

            profile = Profile.objects.get(stripe_customer_id=customer_id)

            stripe_sub = stripe.Subscription.retrieve(sub_id, expand=["items.data.price"])
            sub = _update_subscription_from_stripe(stripe_sub, profile)

            to_email = _profile_email(profile)
            if to_email:
                context = {
                    "name": _profile_name(profile),
                    "plan_name": getattr(sub.plan, "name", "MintKit"),
                    "dashboard_url": _build_url("dashboard", "/"),
                    "portal_url": _build_url("subscriptions_billing_portal", "/subscriptions/portal/"),
                    "pricing_url": _build_url("pricing", "/pricing/"),
                }
                _send_html_email(
                    to_email=to_email,
                    subject="MintKit subscription confirmed ✅",
                    template_name="emails/subscription_confirmed.html",
                    context=context,
                )

        # 2) Subscription updated → detect cancellation request + send email
        elif event_type == "customer.subscription.updated":
            stripe_sub = data_object
            customer_id = stripe_sub.get("customer")
            if not customer_id:
                return HttpResponse(status=200)

            profile = Profile.objects.get(stripe_customer_id=customer_id)

            # Read previous state before updating
            existing = Subscription.objects.filter(
                profile=profile,
                stripe_subscription_id=stripe_sub.get("id")
            ).first()
            old_cancel_flag = bool(getattr(existing, "cancel_at_period_end", False)) if existing else False
            old_status = getattr(existing, "status", None) if existing else None

            sub = _update_subscription_from_stripe(stripe_sub, profile)

            cancel_flag_now = bool(sub.cancel_at_period_end)
            status_now = sub.status

            # Send “you cancelled” email as soon as cancel_at_period_end flips on
            if (not old_cancel_flag) and cancel_flag_now:
                to_email = _profile_email(profile)
                if to_email:
                    period_end = sub.current_period_end.strftime("%d %b %Y") if sub.current_period_end else None
                    context = {
                        "name": _profile_name(profile),
                        "cancel_at_period_end": True,
                        "period_end": period_end,
                        "pricing_url": _build_url("pricing", "/pricing/"),
                    }
                    _send_html_email(
                        to_email=to_email,
                        subject="Your MintKit subscription was cancelled",
                        template_name="emails/subscription_cancelled.html",
                        context=context,
                    )

            # If it actually becomes cancelled, also send (only once on status change)
            if old_status != Subscription.STATUS_CANCELED and status_now == Subscription.STATUS_CANCELED:
                to_email = _profile_email(profile)
                if to_email:
                    period_end = sub.current_period_end.strftime("%d %b %Y") if sub.current_period_end else None
                    context = {
                        "name": _profile_name(profile),
                        "cancel_at_period_end": bool(sub.cancel_at_period_end),
                        "period_end": period_end,
                        "pricing_url": _build_url("pricing", "/pricing/"),
                    }
                    _send_html_email(
                        to_email=to_email,
                        subject="Your MintKit subscription has ended",
                        template_name="emails/subscription_cancelled.html",
                        context=context,
                    )

        # 3) Subscription deleted → definitely cancelled
        elif event_type == "customer.subscription.deleted":
            stripe_sub = data_object
            customer_id = stripe_sub.get("customer")
            if not customer_id:
                return HttpResponse(status=200)

            profile = Profile.objects.get(stripe_customer_id=customer_id)
            sub = _update_subscription_from_stripe(stripe_sub, profile)

            to_email = _profile_email(profile)
            if to_email:
                period_end = sub.current_period_end.strftime("%d %b %Y") if sub.current_period_end else None
                context = {
                    "name": _profile_name(profile),
                    "cancel_at_period_end": bool(sub.cancel_at_period_end),
                    "period_end": period_end,
                    "pricing_url": _build_url("pricing", "/pricing/"),
                }
                _send_html_email(
                    to_email=to_email,
                    subject="Your MintKit subscription has been cancelled",
                    template_name="emails/subscription_cancelled.html",
                    context=context,
                )

    except Exception as exc:
        # IMPORTANT: don’t 500 the webhook (Stripe will keep retrying forever).
        logger.exception("Stripe webhook handling error: %s", exc)
        return HttpResponse(status=200)

    return HttpResponse(status=200)
