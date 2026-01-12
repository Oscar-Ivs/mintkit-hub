# accounts/emails.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrandedLinks:
    """Central place for common site links used in emails."""
    site_root: str = ""
    dashboard_url: str = ""
    about_url: str = ""
    pricing_url: str = ""
    faq_url: str = ""


def _normalise_reply_to(value: Optional[object]) -> Optional[list[str]]:
    """
    Django requires reply_to to be a list/tuple.
    Accepts: None, string, list/tuple.
    """
    if not value:
        return None

    if isinstance(value, (list, tuple)):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return cleaned or None

    cleaned = str(value).strip()
    return [cleaned] if cleaned else None


def _resolve_support_email() -> str:
    """
    Resolve a support/reply-to address used in plain-text fallbacks.
    """
    reply_to = _normalise_reply_to(getattr(settings, "DEFAULT_REPLY_TO_EMAIL", None))
    if reply_to:
        return reply_to[0]
    return "support@mintkit.co.uk"


def _resolve_site_root(request=None) -> str:
    """
    Resolve the site root for absolute URLs.
    Preference:
    1) request.build_absolute_uri("/")
    2) settings.SITE_URL (recommended to set on Heroku)
    """
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")

    site_url = getattr(settings, "SITE_URL", "") or ""
    return site_url.rstrip("/")


def _build_absolute(request, path: str) -> str:
    """
    Convert a URL path into an absolute URL using request or SITE_URL fallback.
    """
    site_root = _resolve_site_root(request)
    if not site_root or not path:
        return ""
    return f"{site_root}{path}"


def _email_asset_urls(request=None) -> Dict[str, str]:
    """
    Provide absolute URLs for images used in email templates.
    - header_bg_url: wide header image (static/img/email.webp)
    - watermark_url: card background image (static/img/card-211.webp)
    - logo_url: optional logo (kept for flexibility)
    """
    header_bg_path = static("img/email.webp")
    watermark_path = static("img/card-211.webp")
    logo_path = static("img/logo-blue.webp")  # optional if templates use it

    return {
        "header_bg_url": _build_absolute(request, header_bg_path),
        "watermark_url": _build_absolute(request, watermark_path),
        "logo_url": _build_absolute(request, logo_path),
    }


def _brand_links(request=None) -> BrandedLinks:
    """Provide absolute site links."""
    site_root = _resolve_site_root(request)
    if not site_root:
        return BrandedLinks()

    return BrandedLinks(
        site_root=site_root,
        dashboard_url=f"{site_root}/accounts/dashboard/",
        about_url=f"{site_root}/about/",
        pricing_url=f"{site_root}/pricing/",
        faq_url=f"{site_root}/faq/",
    )


def _render_plain_fallback(user_name: str, main_line: str, links: BrandedLinks) -> str:
    """Plain-text fallback for clients that block HTML."""
    support_email = _resolve_support_email()

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
        f"Need help? Reply to this email or contact {support_email}.",
    ]
    return "\n".join(lines)


def _resolve_from_email(from_email: Optional[str]) -> str:
    """
    Resolve a safe From address.
    Preference:
    1) Explicit from_email argument
    2) settings.DEFAULT_FROM_EMAIL
    3) settings.EMAIL_HOST_USER
    4) fallback (prevents silent failure in dev)
    """
    if from_email:
        return from_email

    candidate = getattr(settings, "DEFAULT_FROM_EMAIL", "") or ""
    if candidate.strip():
        return candidate.strip()

    candidate = getattr(settings, "EMAIL_HOST_USER", "") or ""
    if candidate.strip():
        return candidate.strip()

    return "webmaster@localhost"


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

    resolved_from = _resolve_from_email(from_email)

    # Default reply-to comes from settings unless explicitly overridden
    effective_reply_to = reply_to if reply_to is not None else getattr(settings, "DEFAULT_REPLY_TO_EMAIL", None)
    reply_to_value = _normalise_reply_to(effective_reply_to) or []

    text_body = context.get("plain_text") or "MintKit notification."
    html_body = render_to_string(template_html, context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=resolved_from,
        to=[to_email],
        reply_to=reply_to_value,
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        sent_count = msg.send(fail_silently=fail_silently)
        return sent_count > 0
    except Exception:
        logger.exception("Email send failed (template=%s, to=%s)", template_html, to_email)
        if fail_silently:
            return False
        raise


def send_welcome_email(user, request=None) -> bool:
    """Send a branded welcome email after successful registration."""
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
        main_line="Your account is ready. MintKit helps small businesses publish digital gift cards, vouchers, and tickets.",
        links=links,
    )

    return send_templated_email(
        subject="Welcome to MintKit",
        to_email=user_email,
        template_html="emails/welcome.html",
        context=context,
        fail_silently=True,
    )

def send_card_received_email(*, to_email: str, viewer_url: str, request=None) -> bool:
    """
    Send a branded “card received” email with a viewer link.
    """
    if not to_email or not viewer_url:
        return False

    links = _brand_links(request)
    assets = _email_asset_urls(request)

    context: Dict[str, Any] = {
        "year": timezone.now().year,
        "site_root": links.site_root,
        "dashboard_url": links.dashboard_url,
        "about_url": links.about_url,
        "pricing_url": links.pricing_url,
        "faq_url": links.faq_url,
        "viewer_url": viewer_url,
        **assets,
    }

    context["plain_text"] = "\n".join(
        [
            "Hi,",
            "",
            "You’ve received a MintKit card.",
            "",
            f"View it here: {viewer_url}",
            "",
            f"Need help? Reply to this email or contact {_resolve_support_email()}.",
        ]
    )

    return send_templated_email(
        subject="You’ve received a MintKit card",
        to_email=to_email,
        template_html="emails/card_received.html",
        context=context,
        fail_silently=False,
    )
