# accounts/emails.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone


@dataclass(frozen=True)
class BrandedLinks:
    site_root: str = ""
    dashboard_url: str = ""
    about_url: str = ""
    pricing_url: str = ""
    faq_url: str = ""


def _build_absolute(request, path: str) -> str:
    """
    Build an absolute URL for a given path using request host.
    Returns empty string if request is missing.
    """
    if request is None:
        return ""
    return request.build_absolute_uri(path)


def _brand_links(request=None) -> BrandedLinks:
    """
    Provide absolute site links for use inside emails.
    """
    if request is None:
        return BrandedLinks()

    site_root = request.build_absolute_uri("/").rstrip("/")
    return BrandedLinks(
        site_root=site_root,
        dashboard_url=f"{site_root}/accounts/dashboard/",
        about_url=f"{site_root}/about/",
        pricing_url=f"{site_root}/pricing/",
        faq_url=f"{site_root}/faq/",
    )


def _email_asset_urls(request=None) -> Dict[str, str]:
    """
    Provide absolute URLs for logo + watermark assets used in email templates.
    """
    # Requested logo:
    logo_path = static("img/email.webp")

    # Watermark image used on About/Pricing/FAQ:
    watermark_path = static("img/card-211.webp")

    return {
        "logo_url": _build_absolute(request, logo_path),
        "watermark_url": _build_absolute(request, watermark_path),
    }


def _normalise_reply_to(value: Optional[Sequence[str] | str]) -> List[str]:
    """
    Django requires reply_to to be a list/tuple.
    Returns an empty list when not provided.
    """
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def _render_plain_fallback(user_name: str, main_line: str, links: BrandedLinks) -> str:
    """
    Plain-text fallback for clients that block HTML emails.
    """
    lines = [
        f"Hi {user_name},",
        "",
        main_line,
    ]

    if links.dashboard_url:
        lines += ["", f"Dashboard: {links.dashboard_url}"]
    if links.site_root:
        lines += ["", f"Website: {links.site_root}"]

    lines += [
        "",
        "Need help? Reply to this email or contact support@mintkit.co.uk.",
    ]
    return "\n".join(lines)


def send_templated_email(
    *,
    subject: str,
    to_email: str,
    template_html: str,
    context: Dict[str, Any],
    from_email: Optional[str] = None,
    reply_to: Optional[Sequence[str] | str] = None,
    fail_silently: bool = True,
) -> bool:
    """
    Send a branded HTML email with a plain-text fallback.
    Returns True if sent, False otherwise.
    """
    if not to_email:
        return False

    resolved_from = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if not resolved_from:
        return False

    # Always pass a list/tuple into EmailMultiAlternatives
    reply_to_list = _normalise_reply_to(
        reply_to or getattr(settings, "DEFAULT_REPLY_TO_EMAIL", "") or ""
    )

    plain_text = context.get("plain_text") or "MintKit notification."
    html_body = render_to_string(template_html, context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        from_email=resolved_from,
        to=[to_email],
        reply_to=reply_to_list,  # must be list/tuple (can be empty list)
    )
    msg.attach_alternative(html_body, "text/html")

    sent = msg.send(fail_silently=fail_silently)
    return sent > 0


def send_welcome_email(user, request=None) -> bool:
    """
    Send a branded welcome email after successful registration.
    """
    user_email = getattr(user, "email", "") or ""
    if not user_email:
        return False

    links = _brand_links(request)
    assets = _email_asset_urls(request)

    context: Dict[str, Any] = {
        "user_name": getattr(user, "username", "there"),
        "year": timezone.now().year,
        "site_root": links.site_root,
        "dashboard_url": links.dashboard_url,
        "about_url": links.about_url,
        "pricing_url": links.pricing_url,
        "faq_url": links.faq_url,
        **assets,
    }

    context["plain_text"] = _render_plain_fallback(
        user_name=context["user_name"],
        main_line="Your account is ready. MintKit helps publish digital cards, vouchers, and tickets with a clean storefront link you can share anywhere.",
        links=links,
    )

    return send_templated_email(
        subject="Welcome to MintKit",
        to_email=user_email,
        template_html="emails/welcome.html",
        context=context,
        fail_silently=True,  # registration should not be blocked by email delivery
    )


def send_subscription_confirmed_email(user, request=None) -> bool:
    """
    Send a subscription confirmation email.
    Call this after Stripe webhook / successful checkout.
    """
    user_email = getattr(user, "email", "") or ""
    if not user_email:
        return False

    links = _brand_links(request)
    assets = _email_asset_urls(request)

    context: Dict[str, Any] = {
        "user_name": getattr(user, "username", "there"),
        "year": timezone.now().year,
        "site_root": links.site_root,
        "dashboard_url": links.dashboard_url,
        "about_url": links.about_url,
        "pricing_url": links.pricing_url,
        "faq_url": links.faq_url,
        **assets,
    }

    context["plain_text"] = _render_plain_fallback(
        user_name=context["user_name"],
        main_line="Your subscription is confirmed. Thanks for supporting MintKit.",
        links=links,
    )

    return send_templated_email(
        subject="Subscription confirmed",
        to_email=user_email,
        template_html="emails/subscription_confirmed.html",
        context=context,
        fail_silently=True,
    )
