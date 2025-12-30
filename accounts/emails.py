# accounts/emails.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone


@dataclass(frozen=True)
class BrandedLinks:
    """Common site links used in transactional emails."""
    site_root: str = ""
    dashboard_url: str = ""
    about_url: str = ""
    pricing_url: str = ""
    faq_url: str = ""


def _build_absolute(request, path_or_url: str) -> str:
    """
    Convert a URL path (or already-resolved URL) into an absolute URL.
    Returns empty string if request is missing.
    """
    if request is None:
        return ""
    return request.build_absolute_uri(path_or_url)


def _email_asset_urls(request=None) -> dict[str, str]:
    """Absolute URLs for images used inside email templates."""
    watermark_path = static("img/card-21.webp")
    logo_path = static("img/logo-22.png")


    return {
        "logo_url": _build_absolute(request, logo_path),
        "watermark_url": _build_absolute(request, watermark_path),
    }


def _brand_links(request=None) -> BrandedLinks:
    """Absolute site links for buttons/anchors inside emails."""
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
    """Plain text fallback for clients that block HTML emails."""
    lines: list[str] = [
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


def _normalise_reply_to(reply_to: Any) -> list[str]:
    """
    Django requires reply_to to be a list/tuple of strings.
    Always returns a LIST (possibly empty) to avoid TypeError.
    """
    if not reply_to:
        return []

    if isinstance(reply_to, (list, tuple)):
        return [str(x) for x in reply_to if x]

    return [str(reply_to)]


def send_templated_email(
    *,
    subject: str,
    to_email: str,
    template_html: str,
    context: dict[str, Any],
    from_email: str | None = None,
    reply_to: list[str] | tuple[str, ...] | str | None = None,
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

    # If reply_to not provided, attempt to use DEFAULT_REPLY_TO_EMAIL from settings
    resolved_reply_to = reply_to
    if resolved_reply_to is None:
        resolved_reply_to = getattr(settings, "DEFAULT_REPLY_TO_EMAIL", [])

    reply_to_list = _normalise_reply_to(resolved_reply_to)

    html_body = render_to_string(template_html, context)
    plain_text = (context.get("plain_text") or "").strip() or "MintKit notification."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        from_email=resolved_from,
        to=[to_email],
        reply_to=reply_to_list,  # MUST be list/tuple, never None
    )
    msg.attach_alternative(html_body, "text/html")

    sent_count = msg.send(fail_silently=fail_silently)
    return sent_count > 0


def send_welcome_email(user, request=None) -> bool:
    """Send a welcome email after successful registration."""
    user_email = getattr(user, "email", "") or ""
    if not user_email:
        return False

    links = _brand_links(request)
    assets = _email_asset_urls(request)

    context: dict[str, Any] = {
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
        main_line="Your account is ready. MintKit helps publish digital cards, vouchers, and tickets.",
        links=links,
    )

    return send_templated_email(
        subject="Welcome to MintKit",
        to_email=user_email,
        template_html="emails/welcome.html",
        context=context,
        fail_silently=True,
    )


def send_subscription_confirmed_email(user, request=None) -> bool:
    """Send a subscription confirmation email (for later Stripe integration)."""
    user_email = getattr(user, "email", "") or ""
    if not user_email:
        return False

    links = _brand_links(request)
    assets = _email_asset_urls(request)

    context: dict[str, Any] = {
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
