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


def _build_absolute(request, path: str) -> str:
    """Convert a URL path into an absolute URL using the incoming request."""
    if request is None:
        return ""
    return request.build_absolute_uri(path)


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


def _render_plain_fallback(user_name: str, main_line: str, links: BrandedLinks) -> str:
    """Plain-text fallback for clients that block HTML."""
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


def _resolve_from_email(from_email: Optional[str]) -> str:
    """
    Resolve a safe From address.
    Preference:
    1) Explicit from_email argument
    2) settings.DEFAULT_FROM_EMAIL
    3) settings.EMAIL_HOST_USER
    4) fallback (won't match DMARC, but prevents silent False)
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
    reply_to_value = _normalise_reply_to(reply_to)

    text_body = context.get("plain_text") or "MintKit notification."
    html_body = render_to_string(template_html, context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=resolved_from,
        to=[to_email],
        reply_to=reply_to_value or [],
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        sent_count = msg.send(fail_silently=fail_silently)
        return sent_count > 0
    except Exception:
        # fail_silently=False will raise here; keep a log either way
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
        # Optional: set reply-to if you have it in settings, otherwise omit
        reply_to=getattr(settings, "DEFAULT_REPLY_TO_EMAIL", None),
        fail_silently=True,
    )
