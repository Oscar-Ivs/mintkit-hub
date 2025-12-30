# accounts/emails.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Union

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone


ReplyToType = Optional[Union[str, Sequence[str]]]


@dataclass(frozen=True)
class BrandedLinks:
    """
    Central place for common site links used in emails.
    """
    site_root: str = ""
    dashboard_url: str = ""
    about_url: str = ""
    pricing_url: str = ""
    faq_url: str = ""


def _site_root(request=None) -> str:
    """
    Return absolute site root where possible.
    - request present -> uses request.build_absolute_uri
    - otherwise -> uses SITE_URL if defined (optional)
    """
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")
    return (getattr(settings, "SITE_URL", "") or "").rstrip("/")


def _abs_url(request, path_or_url: str) -> str:
    """
    Convert a path (/static/...) into an absolute URL if possible.
    If it's already absolute (http...), return as-is.
    """
    if not path_or_url:
        return ""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url

    root = _site_root(request)
    if not root:
        # No request + no SITE_URL; return path as-is (useful for local preview files)
        return path_or_url

    if not path_or_url.startswith("/"):
        path_or_url = "/" + path_or_url
    return f"{root}{path_or_url}"


def _email_asset_urls(request=None) -> Dict[str, str]:
    """
    Absolute URLs for images used in email templates.
    """
    logo_path = static("img/logo_small.webp")
    watermark_path = static("img/card-21.webp")

    return {
        "logo_url": _abs_url(request, logo_path),
        "watermark_url": _abs_url(request, watermark_path),
    }


def _brand_links(request=None) -> BrandedLinks:
    """
    Absolute links used in emails.
    """
    root = _site_root(request)
    if not root:
        return BrandedLinks()

    return BrandedLinks(
        site_root=root,
        dashboard_url=f"{root}/accounts/dashboard/",
        about_url=f"{root}/about/",
        pricing_url=f"{root}/pricing/",
        faq_url=f"{root}/faq/",
    )


def _render_plain_fallback(user_name: str, main_line: str, links: BrandedLinks) -> str:
    """
    Plain-text fallback for email clients that block HTML.
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

    lines += ["", "Need help? Reply to this email or contact support@mintkit.co.uk."]
    return "\n".join(lines)


def _normalise_reply_to(reply_to: ReplyToType) -> Optional[list[str]]:
    """
    Django requires reply_to to be a list or tuple (or None).
    Accepts a string or a sequence and normalises to list[str].
    """
    if not reply_to:
        return None

    if isinstance(reply_to, str):
        value = reply_to.strip()
        return [value] if value else None

    # Sequence of strings
    cleaned: list[str] = []
    for item in reply_to:
        if item:
            cleaned.append(str(item).strip())
    return cleaned or None


def send_templated_email(
    *,
    subject: str,
    to_email: str,
    template_html: str,
    context: Dict[str, Any],
    from_email: Optional[str] = None,
    reply_to: ReplyToType = None,
    fail_silently: bool = True,
) -> bool:
    """
    Send an HTML email (template) + plain-text fallback.
    Returns True if sent, False otherwise.
    """
    if not to_email:
        return False

    resolved_from = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if not resolved_from:
        return False

    # If reply_to not passed, try a default single address from settings (string is fine here)
    default_reply_to = getattr(settings, "DEFAULT_REPLY_TO_EMAIL", None)
    reply_to_list = _normalise_reply_to(reply_to or default_reply_to)

    html_body = render_to_string(template_html, context)
    text_body = context.get("plain_text") or "MintKit notification."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=resolved_from,
        to=[to_email],
        reply_to=reply_to_list,  # must be list/tuple or None
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        sent_count = msg.send(fail_silently=fail_silently)
        return sent_count > 0
    except Exception:
        if fail_silently:
            return False
        raise


def send_welcome_email(user, request=None) -> bool:
    """
    Send welcome email after successful registration.
    Skips if user.email is empty.
    """
    user_email = (getattr(user, "email", "") or "").strip()
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
    """
    Subscription confirmation email (call after Stripe success / webhook).
    """
    user_email = (getattr(user, "email", "") or "").strip()
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
