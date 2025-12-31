# accounts/emails.py
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone

logger = logging.getLogger(__name__)


def _site_root(request=None) -> str:
    """
    Best-effort site root for absolute links in emails.
    """
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")
    return getattr(settings, "SITE_ROOT", "").rstrip("/")


def _abs(request, path_or_url: str) -> str:
    """
    Convert /static/... or /path/... into an absolute URL when possible.
    """
    if not path_or_url:
        return ""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    root = _site_root(request)
    if not root:
        return path_or_url
    if not path_or_url.startswith("/"):
        path_or_url = "/" + path_or_url
    return f"{root}{path_or_url}"


def _normalise_reply_to(value) -> list[str] | None:
    """
    Django requires reply_to to be a list/tuple.
    """
    if not value:
        return None
    if isinstance(value, (list, tuple)):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return cleaned or None
    return [str(value).strip()]


def send_templated_email(
    *,
    subject: str,
    to_email: str,
    template_html: str,
    context: dict[str, Any],
    from_email: str | None = None,
    reply_to=None,
    fail_silently: bool = True,
) -> bool:
    """
    Send a HTML email with a plain-text fallback.
    """
    if not to_email:
        return False

    resolved_from = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if not resolved_from:
        return False

    html_body = render_to_string(template_html, context)
    text_body = context.get("plain_text") or "MintKit notification."

    reply_to_list = _normalise_reply_to(reply_to) or _normalise_reply_to(
        getattr(settings, "DEFAULT_REPLY_TO_EMAIL", None)
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=resolved_from,
            to=[to_email],
            reply_to=reply_to_list,
        )
        msg.attach_alternative(html_body, "text/html")
        sent = msg.send(fail_silently=fail_silently)
        return bool(sent)
    except Exception:
        if fail_silently:
            logger.exception("Email send failed (subject=%s, to=%s)", subject, to_email)
            return False
        raise


def send_welcome_email(user, request=None) -> bool:
    """
    Welcome email sent after successful registration.
    """
    user_email = getattr(user, "email", "") or ""
    if not user_email:
        return False

    site_root = _site_root(request)
    assets = {
        "logo_url": _abs(request, static("img/email.webp")),
        "watermark_url": _abs(request, static("img/card-211.webp")),
    }

    context: dict[str, Any] = {
        "user_name": getattr(user, "username", "there"),
        "year": timezone.now().year,
        "site_root": site_root,
        "dashboard_url": f"{site_root}/accounts/dashboard/" if site_root else "/accounts/dashboard/",
        "about_url": f"{site_root}/about/" if site_root else "/about/",
        "pricing_url": f"{site_root}/pricing/" if site_root else "/pricing/",
        "faq_url": f"{site_root}/faq/" if site_root else "/faq/",
        **assets,
    }

    context["plain_text"] = "\n".join(
        [
            f"Welcome to MintKit, {context['user_name']}!",
            "",
            "Your account is ready. MintKit helps small businesses publish digital gift cards, vouchers, and tickets.",
            "",
            f"Dashboard: {context['dashboard_url']}",
            "",
            "Need help? Reply to this email or contact support@mintkit.co.uk.",
        ]
    )

    return send_templated_email(
        subject="Welcome to MintKit",
        to_email=user_email,
        template_html="emails/welcome.html",
        context=context,
        reply_to=["support@mintkit.co.uk"],
        fail_silently=True,
    )
