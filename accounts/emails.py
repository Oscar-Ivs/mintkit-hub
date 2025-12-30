# accounts/emails.py
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


def send_welcome_email(user, request=None):
    """
    Send a branded welcome email to the user's email address.
    Uses HTML template + plain-text fallback.
    """
    if not getattr(user, "email", ""):
        return  # No email on the user; skip silently

    site_root = ""
    if request is not None:
        site_root = request.build_absolute_uri("/").rstrip("/")

    context = {
        "user_name": user.username,
        "year": timezone.now().year,
        "dashboard_url": f"{site_root}/accounts/dashboard/" if site_root else "",
        "about_url": f"{site_root}/about/" if site_root else "",
        "pricing_url": f"{site_root}/pricing/" if site_root else "",
        "faq_url": f"{site_root}/faq/" if site_root else "",
        # Optional watermark (can be empty if not hosted yet)
        "watermark_url": "",
    }

    subject = "Welcome to MintKit"
    text_body = (
        f"Welcome to MintKit, {user.username}!\n\n"
        "Your account is ready.\n"
        "If you need help, reply to this email.\n"
    )

    html_body = render_to_string("emails/welcome.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        reply_to=[getattr(settings, "DEFAULT_REPLY_TO_EMAIL", "support@mintkit.co.uk")],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
