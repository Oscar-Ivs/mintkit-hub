# studio_bridge/views.py
import base64
import json
import logging
from io import BytesIO
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.emails import send_card_received_email
from .models import CardLink

logger = logging.getLogger(__name__)

try:
    import qrcode
except Exception:  # keeps production safe if dependency missing
    qrcode = None


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def _rate_limit_ok(request) -> bool:
    # Basic protection: 10 requests per 5 minutes per IP
    ip = _client_ip(request)
    key = f"studio_send:{ip}"
    count = cache.get(key, 0)
    if count >= 10:
        return False
    cache.set(key, count + 1, timeout=300)
    return True


def _open_url_allowed(open_url: str) -> bool:
    """
    Allows only trusted destinations.
    Uses hostname matching (not substring matching) to prevent abuse.
    """
    try:
        host = (urlparse(open_url).hostname or "").lower()
    except Exception:
        return False

    if not host:
        return False

    allowed_exact = {
        "mintkit.co.uk",
        "mintkit-smr.caffeine.xyz",
    }
    allowed_suffixes = (
        "caffeine.xyz",
        "ic0.app",
        "icp0.io",
        "raw.icp0.io",
    )

    if host in allowed_exact:
        return True

    return any(host == s or host.endswith(f".{s}") for s in allowed_suffixes)


def _make_qr_data_uri(payload: str) -> str:
    """
    Create a scannable PNG QR (data URI) for Hub viewer pages.
    Uses ECC=M (same as your original external QR service).
    """
    if not payload or qrcode is None:
        return ""

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,  # quiet zone
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def card_viewer(request, token):
    link = get_object_or_404(CardLink, token=token)

    # Viewer page is under mintkit.co.uk, so keep everything on this domain:
    # QR content is the manual code (works even if dynamic rotation changes later).
    manual_code = f"MANUAL-{link.nft_id}"
    qr_code_data_uri = _make_qr_data_uri(manual_code)

    return render(
        request,
        "studio_bridge/card_viewer.html",
        {
            "link": link,
            "manual_code": manual_code,
            "qr_code_data_uri": qr_code_data_uri,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def send_card_email_api(request):
    expected = (getattr(settings, "STUDIO_API_KEY", "") or "").strip()
    provided = (request.META.get("HTTP_X_STUDIO_KEY", "") or "").strip()
    if not expected or provided != expected:
        return JsonResponse({"success": False, "error": "Forbidden"}, status=403)

    if not _rate_limit_ok(request):
        return JsonResponse({"success": False, "error": "Rate limit exceeded"}, status=429)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    recipient_email = (payload.get("recipient_email") or "").strip()
    nft_id = (payload.get("nft_id") or "").strip()
    open_url = (payload.get("open_url") or "").strip()
    image_url = (payload.get("image_url") or "").strip()

    if not recipient_email or not nft_id or not open_url:
        return JsonResponse(
            {"success": False, "error": "recipient_email, nft_id and open_url are required"},
            status=400,
        )

    if not _open_url_allowed(open_url):
        return JsonResponse({"success": False, "error": "open_url domain not allowed"}, status=400)

    link = CardLink.objects.create(
        nft_id=nft_id,
        open_url=open_url,
        image_url=image_url,
        recipient_email=recipient_email,
    )

    site = (settings.SITE_URL or "").rstrip("/")
    viewer_url = f"{site}/v/{link.token}/"

    try:
        sent = send_card_received_email(
            to_email=recipient_email,
            viewer_url=viewer_url,
            card_image_url=image_url or None,
            card_id=nft_id,
            request=None,
        )
    except Exception as exc:
        logger.exception("Send card email failed: %s", exc)
        return JsonResponse({"success": False, "error": "Email send failed"}, status=500)

    if not sent:
        return JsonResponse({"success": False, "error": "Email send failed"}, status=500)

    return JsonResponse({"success": True, "viewer_url": viewer_url})
