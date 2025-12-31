# accounts/emails.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Union
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrandedLinks:
    site_root: str
    dashboard_url: str
    about_url: str
    pricing_url: str
    faq_url: str


def _site_root_from_request(request) -> str:
    if request is None:
        return ""
    return request.build_absolute_uri("/").rstrip("/")


def _site_root_fallback() -> str:
    # Optional: add SITE_URL="https://mintkit.co.uk" in env for non-request contexts
    site_url = getattr(settings, "SITE_URL", "") or ""
    return site_url.rstrip("/")


def get_site_root(request=None) -> str:
    return _site_root_from_request(request) or _site_root_fallback()


def _abs(site_root: str, path: str) -> str:
    # path may be /static/... or already absolute
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not site_root:
        return ""
    return urljoin(f"{site_root}/", path.lstrip("/"))


def build_links(site_root: str) -> BrandedLinks:
    return BrandedLinks(
        site_root=site_root,
        dashboard_url=f"{site_root}/accounts/dashboard/" if site_root else "",
        about_url=f"{site_root}/about/" if site_root else "",
        pricing_url=f"{site_root}/pricing/" if site_root else "",
        faq_url=f"{site_root}/faq/" if site_root else "",
    )


def build_assets(site_root: str) -> Dict[str, str]:
    # Header banner image you created
    header_image_path = static("img/email.webp")

    # Watermark image
    watermark_path = static("img/card-211.webp")

    return {
        "header_image_url": _abs(site_root, header_image_path),
        "logo_url": _abs(site_root, logo_path),
        "watermark_url": _abs(site_root, watermark_path),
    }


def build_common_email_context(*, request=None, user_name: str = "there") -> Dict[str, Any]:
    site_root = get_site_root(request)
    links = build_links(site_root)
    assets = build_assets(site_root)

    return {
        "user_name": user_name,
        "site_root": links.site_root,
        "dashboard_url": links.dashboard_url,
        "about_url": links.about_url,
        "pricing_url": links.pricing_url,
        "faq_url": links.faq_url,
        "year": timezone.now().year,
        **assets,
    }


def _render_plain_fallback(user_name: str, main_line: str, links: BrandedLinks) -> str:
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


def _clean_reply_to(reply_to: Optional[Union[str, Sequence[str]]]) -> Optional[list[str]]:
    if not reply_to:
        return None

    if isinstance(reply_to, (list, tuple, set)):
        cleaned = [str(x).strip() for x in reply_to if str(x).strip()]
        return cleaned or None

    # single string
    val = str(reply_to).strip()
    return [val] if val else None


def send_templated_email(
    *,
    subject: str,
    to_email: str,
    template_html: str,
    context: Dict[str, Any],
    from_email: Optional[str] = None,
    reply_to: Optional[Union[str, Sequence[str]]] = None,
    fail_silently: bool = True,
) -> bool:
    if not to_email:
        return False

    resolved_from = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if not resolved_from:
        return False

    html_body = render_to_string(template_html, context)
    text_body = context.get("plain_text") or "MintKit notification."

    reply_to_clean = _clean_reply_to(reply_to)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=resolved_from,
        to=[to_email],
        reply_to=reply_to_clean,  # must be list/tuple or None
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        sent_count = msg.send(fail_silently=fail_silently)
        return sent_count > 0
    except Exception:
        # Never crash business flows because SMTP is down
        logger.exception("Email send failed: subject=%s to=%s", subject, to_email)
        if fail_silently:
            return False
        raise


def send_welcome_email(user, request=None) -> bool:
    user_email = (getattr(user, "email", "") or "").strip()
    if not user_email:
        return False

    site_root = get_site_root(request)
    links = build_links(site_root)

    context = build_common_email_context(
        request=request,
        user_name=getattr(user, "username", "there"),
    )

    context["plain_text"] = _render_plain_fallback(
        user_name=context["user_name"],
        main_line="Your account is ready. MintKit helps publish digital gift cards, vouchers, and tickets.",
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
    user_email = (getattr(user, "email", "") or "").strip()
    if not user_email:
        return False

    site_root = get_site_root(request)
    links = build_links(site_root)

    context = build_common_email_context(
        request=request,
        user_name=getattr(user, "username", "there"),
    )

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
