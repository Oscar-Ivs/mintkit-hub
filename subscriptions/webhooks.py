# subscriptions/webhooks.py
import datetime
import logging
from urllib.parse import urlsplit

import stripe
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import Profile
from .models import Subscription, SubscriptionPlan, PmbSubscription
from .stripe_service import init_stripe

logger = logging.getLogger(__name__)


def _utc_from_ts(ts):
    """Stripe timestamps are unix seconds; convert to timezone-aware UTC datetime."""
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


def _profile_email(profile: Profile) -> str:
    """Preferred email for subscription notifications."""
    return (getattr(profile, "contact_email", "") or profile.user.email or "").strip()


def _site_parts():
    """Return (protocol, domain, site_root) based on SITE_URL."""
    raw_site = (getattr(settings, "SITE_URL", "") or "").strip().rstrip("/")
    if not raw_site:
        return "http", "127.0.0.1:8000", "http://127.0.0.1:8000"

    parts = urlsplit(raw_site)
    if parts.scheme and parts.netloc:
        protocol = parts.scheme
        domain = parts.netloc
        site_root = f"{protocol}://{domain}"
        return protocol, domain, site_root

    # Fallback if SITE_URL stored without scheme
    domain = raw_site.replace("https://", "").replace("http://", "").split("/")[0]
    protocol = "https"
    site_root = f"{protocol}://{domain}"
    return protocol, domain, site_root


def _base_email_ctx(profile: Profile, plan_name: str):
    """Base context used by templates/emails/base_email.html."""
    protocol, domain, site_root = _site_parts()

    return {
        "first_name": profile.user.first_name or profile.user.username,
        "plan_name": plan_name,

        "protocol": protocol,
        "domain": domain,
        "site_root": site_root,

        # Internal app URLs
        "dashboard_url": f"{site_root}/accounts/dashboard/",
        "portal_url": f"{site_root}/subscriptions/portal/",

        # Footer links
        "support_email": "support@mintkit.co.uk",
        "about_url": f"{site_root}/about/",
        "pricing_url": f"{site_root}/pricing/",
        "faq_url": f"{site_root}/faq/",
    }


def _send_email(template_html, template_txt, subject, to_email, ctx):
    """Send both HTML and text versions."""
    html_body = render_to_string(template_html, ctx)
    txt_body = render_to_string(template_txt, ctx)

    msg = EmailMultiAlternatives(subject=subject, body=txt_body, to=[to_email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


def _find_profile_for_subscription(stripe_sub):
    """
    Prefer subscription metadata (set at Checkout creation).
    Fallback to local DB via stripe_subscription_id.
    """
    md = stripe_sub.get("metadata") or {}
    profile_id = md.get("profile_id")

    if profile_id:
        try:
            return Profile.objects.get(pk=profile_id)
        except Profile.DoesNotExist:
            return None

    sub_id = stripe_sub.get("id")
    local = (
        Subscription.objects.select_related("profile")
        .filter(stripe_subscription_id=sub_id)
        .first()
    )
    return local.profile if local else None


def _map_stripe_status(stripe_status: str) -> str:
    status = (stripe_status or "").strip().lower()
    status_map = {
        "active": Subscription.STATUS_ACTIVE,
        "trialing": Subscription.STATUS_TRIALING,
        "past_due": Subscription.STATUS_PAST_DUE,
        "unpaid": Subscription.STATUS_PAST_DUE,
        "incomplete": Subscription.STATUS_INCOMPLETE,
        "incomplete_expired": Subscription.STATUS_INCOMPLETE,
        "canceled": Subscription.STATUS_CANCELED,
        "cancelled": Subscription.STATUS_CANCELED,
    }
    return status_map.get(status, Subscription.STATUS_CANCELED)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe webhook endpoint."""
    init_stripe()

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    event_type = event.get("type", "")
    obj = event["data"]["object"]

    try:
        # ------------------------------------------------------------
        # 1) Checkout completed
        # ------------------------------------------------------------
        if event_type == "checkout.session.completed":
            session = obj
            stripe_sub_id = session.get("subscription")
            if not stripe_sub_id:
                return HttpResponse(status=200)

            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)

            md = session.get("metadata") or stripe_sub.get("metadata") or {}
            plan_code = (md.get("plan_code") or "basic").strip().lower()
            profile_id = md.get("profile_id")

            profile = Profile.objects.filter(pk=profile_id).first() if profile_id else None
            if not profile:
                profile = _find_profile_for_subscription(stripe_sub)
            if not profile:
                logger.warning("Webhook: cannot link checkout to profile (missing metadata/profile).")
                return HttpResponse(status=200)

            customer_id = session.get("customer") or stripe_sub.get("customer")
            if customer_id and hasattr(profile, "stripe_customer_id"):
                if profile.stripe_customer_id != customer_id:
                    profile.stripe_customer_id = customer_id
                    profile.save(update_fields=["stripe_customer_id"])

            plan = SubscriptionPlan.objects.filter(code=plan_code).first()
            if not plan:
                logger.warning("Webhook: plan not found in DB: %s", plan_code)
                return HttpResponse(status=200)

            new_status = _map_stripe_status(stripe_sub.get("status"))
            cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
            cancel_at = _utc_from_ts(stripe_sub.get("cancel_at"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at"))
            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))

            existing = Subscription.objects.filter(
                profile=profile,
                stripe_subscription_id=stripe_sub_id,
            ).first()
            prev_status = existing.status if existing else None

            sub_obj, _ = Subscription.objects.update_or_create(
                profile=profile,
                stripe_subscription_id=stripe_sub_id,
                defaults={
                    "plan": plan,
                    "status": new_status,
                    "stripe_customer_id": customer_id or "",
                    "current_period_end": current_period_end,
                    "cancel_at_period_end": cancel_at_period_end,
                    "cancel_at": cancel_at,
                    "canceled_at": canceled_at,
                },
            )

            # Cancel local trial record if paid activated
            if plan_code != "trial":
                Subscription.objects.filter(
                    profile=profile,
                    plan__code="trial",
                    status=Subscription.STATUS_TRIALING,
                    stripe_subscription_id="",
                ).update(
                    status=Subscription.STATUS_CANCELED,
                    canceled_at=datetime.datetime.now(tz=datetime.timezone.utc),
                    cancel_at=None,
                    cancel_at_period_end=False,
                )

            # Send "active" email only on transition to ACTIVE
            if prev_status != Subscription.STATUS_ACTIVE and sub_obj.status == Subscription.STATUS_ACTIVE:
                to_email = _profile_email(profile)
                if to_email:
                    ctx = _base_email_ctx(profile, plan.name)
                    _send_email(
                        "emails/subscription_confirmed.html",
                        "emails/subscription_confirmed.txt",
                        f"Your MintKit {plan.name} subscription is active ✅",
                        to_email,
                        ctx,
                    )

               # ------------------------------------------------------------
        # 2) Subscription updated (cancel scheduled/resumed/etc)
        # ------------------------------------------------------------
        elif event_type == "customer.subscription.updated":
            stripe_sub = obj

            profile = _find_profile_for_subscription(stripe_sub)
            if not profile:
                return HttpResponse(status=200)

            sub_id = stripe_sub.get("id")
            existing = Subscription.objects.filter(profile=profile, stripe_subscription_id=sub_id).first()

            stripe_status = (stripe_sub.get("status") or "").strip().lower()
            new_status = _map_stripe_status(stripe_status)

            cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
            cancel_at = _utc_from_ts(stripe_sub.get("cancel_at"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at"))
            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))
            customer_id = stripe_sub.get("customer")

            md = stripe_sub.get("metadata") or {}
            plan_code = (md.get("plan_code") or "basic").strip().lower()
            plan = SubscriptionPlan.objects.filter(code=plan_code).first()

            # If metadata is missing, keep previous plan if available
            if not plan and existing:
                plan = existing.plan
            if not plan:
                logger.warning("Webhook: cannot resolve plan for sub=%s (no metadata and no local plan).", sub_id)
                return HttpResponse(status=200)

            prev_status = existing.status if existing else None
            prev_cancel_flag = existing.cancel_at_period_end if existing else False
            prev_cancel_at = existing.cancel_at if existing else None

            sub_obj, _ = Subscription.objects.update_or_create(
                profile=profile,
                stripe_subscription_id=sub_id,
                defaults={
                    "plan": plan,
                    "status": new_status,
                    "stripe_customer_id": customer_id or "",
                    "current_period_end": current_period_end,
                    "cancel_at_period_end": cancel_at_period_end,
                    "cancel_at": cancel_at,
                    "canceled_at": canceled_at,
                },
            )

            # Stripe can represent "scheduled cancellation" in two ways:
            # - cancel_at_period_end=True (end of billing period)
            # - cancel_at=<timestamp>     (portal sometimes sets this while leaving cancel_at_period_end False)
            scheduled_now = bool(cancel_at_period_end or (cancel_at is not None))
            scheduled_prev = bool(prev_cancel_flag or (prev_cancel_at is not None))

            # Use cancel_at if present, otherwise fall back to current_period_end
            ends_on = cancel_at or current_period_end

            logger.warning(
                "CANCEL CHECK: sub=%s scheduled_prev=%s scheduled_now=%s prev_cap_end=%s prev_cancel_at=%s "
                "cap_end=%s cancel_at=%s new_status=%s stripe_status=%s",
                sub_id,
                scheduled_prev,
                scheduled_now,
                prev_cancel_flag,
                prev_cancel_at,
                cancel_at_period_end,
                cancel_at,
                new_status,
                stripe_status,
            )

            # Email when user schedules cancellation (either style)
            if (not scheduled_prev) and scheduled_now and new_status in (
                Subscription.STATUS_ACTIVE,
                Subscription.STATUS_TRIALING,
            ):
                to_email = _profile_email(profile)
                if to_email:
                    logger.warning(
                        "CANCEL EMAIL PATH HIT: sub=%s to=%s ends_on=%s cap_end=%s cancel_at=%s status=%s",
                        sub_id,
                        to_email,
                        ends_on,
                        cancel_at_period_end,
                        cancel_at,
                        stripe_status,
                    )

                    ctx = _base_email_ctx(profile, plan.name)
                    ctx.update(
                        {
                            "ends_on": ends_on,
                            "manage_url": ctx["portal_url"],
                            "site_url": ctx["site_root"],
                        }
                    )
                    _send_email(
                        "emails/subscription_cancelled.html",
                        "emails/subscription_cancelled.txt",
                        "Your MintKit subscription will end (unless resumed)",
                        to_email,
                        ctx,
                    )

            # Email when cancelled immediately (status becomes canceled)
            if prev_status != Subscription.STATUS_CANCELED and sub_obj.status == Subscription.STATUS_CANCELED:
                to_email = _profile_email(profile)
                if to_email:
                    ctx = _base_email_ctx(profile, plan.name)
                    ctx.update(
                        {
                            "ends_on": current_period_end,
                            "manage_url": ctx["portal_url"],
                            "site_url": ctx["site_root"],
                        }
                    )
                    _send_email(
                        "emails/subscription_cancelled.html",
                        "emails/subscription_cancelled.txt",
                        "Your MintKit subscription has been cancelled",
                        to_email,
                        ctx,
                    )

        # ------------------------------------------------------------
        # 3) Subscription deleted (ended)
        # ------------------------------------------------------------
        elif event_type == "customer.subscription.deleted":
            stripe_sub = obj

            profile = _find_profile_for_subscription(stripe_sub)
            if not profile:
                return HttpResponse(status=200)

            sub_id = stripe_sub.get("id")
            sub_obj = Subscription.objects.filter(profile=profile, stripe_subscription_id=sub_id).first()

            current_period_end = _utc_from_ts(stripe_sub.get("current_period_end"))
            canceled_at = _utc_from_ts(stripe_sub.get("canceled_at")) or datetime.datetime.now(tz=datetime.timezone.utc)

            if sub_obj:
                sub_obj.status = Subscription.STATUS_CANCELED
                sub_obj.cancel_at_period_end = False
                sub_obj.cancel_at = None
                sub_obj.canceled_at = canceled_at
                sub_obj.save(update_fields=["status", "cancel_at_period_end", "cancel_at", "canceled_at"])

                # Email: always notify on DELETE events (service ended)
                to_email = _profile_email(profile)
                if to_email:
                    plan_name = sub_obj.plan.name if sub_obj.plan else "subscription"
                    ctx = _base_email_ctx(profile, plan_name)
                    ctx.update(
                        {
                            "ends_on": current_period_end,
                            "manage_url": ctx["portal_url"],
                            "site_url": ctx["site_root"],
                        }
                    )
                    _send_email(
                        "emails/subscription_cancelled.html",
                        "emails/subscription_cancelled.txt",
                        "Your MintKit subscription has ended",
                        to_email,
                        ctx,
                    )

    except Exception:
        # Keep 200 so Stripe won’t spam retries, but log properly
        logger.exception("Stripe webhook processing failed for event=%s", event_type)

    return HttpResponse(status=200)
# -------------------------
# PlanMyBalance Stripe webhook (separate Stripe account/keys)
# -------------------------
@csrf_exempt
@require_POST
def stripe_webhook_pmb(request):
    """
    Stripe webhook for PlanMyBalance (separate Stripe account/keys).
    Verifies signature using PMB_STRIPE_WEBHOOK_SECRET, then upserts PmbSubscription.

    Important:
    - Billing Portal plan changes often DO NOT update subscription.metadata.
    - So we MUST infer the plan from the active subscription item price IDs
      and prefer that over metadata if it matches known prices.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    webhook_secret = (getattr(settings, "PMB_STRIPE_WEBHOOK_SECRET", "") or "").strip()
    if not webhook_secret:
        logger.error("PMB webhook called but PMB_STRIPE_WEBHOOK_SECRET is missing.")
        return HttpResponse(status=500)

    pmb_key = (getattr(settings, "PMB_STRIPE_SECRET_KEY", "") or "").strip()
    if not pmb_key:
        logger.error("PMB webhook called but PMB_STRIPE_SECRET_KEY is missing.")
        return HttpResponse(status=500)

    old_key = stripe.api_key
    stripe.api_key = pmb_key

    def _utc_from_ts(ts):
        if not ts:
            return None
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except Exception:
            return None

    def _infer_plan_from_subscription(subscription):
        """
        Return 'basic'/'pro'/'supporter' if we can match by price id, else ''.
        Prefer higher tiers if multiple items exist during proration transitions.
        """
        basic_price = (getattr(settings, "PMB_STRIPE_PRICE_BASIC", "") or "").strip()
        pro_price = (getattr(settings, "PMB_STRIPE_PRICE_PRO", "") or "").strip()
        supporter_price = (getattr(settings, "PMB_STRIPE_PRICE_SUPPORTER", "") or "").strip()

        price_ids = []

        try:
            items = ((subscription.get("items") or {}).get("data")) or []
            for it in items:
                pid = (((it.get("price") or {}).get("id")) or "").strip()
                if pid:
                    price_ids.append(pid)
        except Exception:
            pass

        # Priority: supporter > pro > basic
        if supporter_price and supporter_price in price_ids:
            return "supporter"
        if pro_price and pro_price in price_ids:
            return "pro"
        if basic_price and basic_price in price_ids:
            return "basic"

        return ""

    def _upsert_from_subscription(subscription, principal_id=None, plan_code=None):
        if not subscription:
            return

        sub_id = (subscription.get("id") or "").strip()
        customer_id = (subscription.get("customer") or "").strip()
        status = (subscription.get("status") or "").strip()
        current_period_end = _utc_from_ts(subscription.get("current_period_end"))

        meta = subscription.get("metadata") or {}
        principal = (principal_id or meta.get("principal_id") or meta.get("principalId") or "").strip()

        # Plan from metadata / session
        plan_meta = (plan_code or meta.get("plan_code") or meta.get("plan") or "").strip().lower()

        # Plan from Stripe subscription items (this is what changes on Billing Portal upgrades)
        plan_price = _infer_plan_from_subscription(subscription)

        # Prefer price-derived plan when it matches a known tier
        plan = plan_price if plan_price in ("basic", "pro", "supporter") else plan_meta

        # --- principal fallback (Billing Portal updates may lose metadata) ---
        if not principal:
            existing = None
            if sub_id:
                existing = PmbSubscription.objects.filter(stripe_subscription_id=sub_id).first()
            if not existing and customer_id:
                existing = PmbSubscription.objects.filter(stripe_customer_id=customer_id).first()

            if existing:
                principal = (existing.principal_id or "").strip()
            else:
                logger.warning(
                    "PMB webhook: missing principal_id and no local match (sub=%s customer=%s)",
                    sub_id,
                    customer_id,
                )
                return

        # If plan still unknown, keep existing tier, else default to free
        if plan not in ("basic", "pro", "supporter"):
            prior = PmbSubscription.objects.filter(principal_id=principal).first()
            plan = prior.tier if prior else "free"

        rec, _ = PmbSubscription.objects.update_or_create(
            principal_id=principal,
            defaults={
                "tier": plan,
                "status": status,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": sub_id,
                "current_period_end": current_period_end,
            },
        )

        logger.info(
            "PMB subscription upserted: principal=%s tier=%s status=%s sub=%s",
            rec.principal_id,
            rec.tier,
            rec.status,
            rec.stripe_subscription_id,
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret,
        )

        event_type = (event.get("type") or "").strip()
        obj = (event.get("data") or {}).get("object") or {}

        logger.info("PMB webhook received: %s", event_type)

        if event_type == "checkout.session.completed":
            # Best event for capturing principal + plan metadata
            principal_id = (obj.get("client_reference_id") or "").strip()
            meta = obj.get("metadata") or {}
            plan_code = (meta.get("plan_code") or meta.get("plan") or "").strip().lower()

            subscription_id = obj.get("subscription")
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                _upsert_from_subscription(subscription, principal_id=principal_id, plan_code=plan_code)
            else:
                logger.warning("PMB checkout.session.completed had no subscription id")

        elif event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            # Billing Portal upgrades show up here; metadata may be stale -> price inference fixes it
            _upsert_from_subscription(obj)

        elif event_type == "invoice.payment_failed":
            subscription_id = obj.get("subscription")
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                _upsert_from_subscription(subscription)

        return HttpResponse(status=200)

    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception("PMB webhook error: %s", e)
        return HttpResponse(status=500)
    finally:
        stripe.api_key = old_key
