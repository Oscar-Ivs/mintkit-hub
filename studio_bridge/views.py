import json
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.emails import send_card_received_email
from .models import CardLink


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


def _host_allowed(url: str) -> bool:
    """
    Safety check to reduce endpoint abuse:
    Only allow known domains for open_url (and optionally image_url).
    """
    url = (url or "").strip()
    if not url:
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    host = (parsed.hostname or "").lower()
    scheme = (parsed.scheme or "").lower()

    if not host or scheme not in ("https", "http"):
        return False

    # Allow localhost during development if needed
    if host in ("localhost", "127.0.0.1"):
        return True

    allowed_suffixes = (
        "caffeine.xyz",  # app domain
        "ic0.app",       # ICP gateway
        "icp0.io",       # ICP gateway (includes raw.icp0.io)
        "mintkit.co.uk", # hub site domain
    )

    return any(host == s or host.endswith("." + s) for s in allowed_suffixes)


def card_viewer(request, token):
    link = get_object_or_404(CardLink, token=token)
    return render(request, "studio_bridge/card_viewer.html", {"link": link})


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def send_card_email_api(request):
    # Preflight
    if request.method == "OPTIONS":
        return HttpResponse(status=204)

    expected = (getattr(settings, "STUDIO_API_KEY", "") or "").strip()
    provided = (request.headers.get("X-STUDIO-KEY", "") or "").strip()

    if not expected or provided != expected:
        # Always return JSON so frontend can parse safely
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

    # Allowlist open_url destinations (important for raw.icp0.io)
    if not _host_allowed(open_url):
        return JsonResponse({"success": False, "error": "open_url domain not allowed"}, status=400)

    # Optional: if you want to be strict with image_url too
    if image_url and not _host_allowed(image_url):
        return JsonResponse({"success": False, "error": "image_url domain not allowed"}, status=400)

    link = CardLink.objects.create(
        nft_id=nft_id,
        open_url=open_url,
        image_url=image_url,
        recipient_email=recipient_email,
    )

    site_url = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    viewer_url = f"{site_url}/v/{link.token}/"

    sent = send_card_received_email(
        to_email=recipient_email,
        viewer_url=viewer_url,
        request=None,
    )

    if not sent:
        return JsonResponse({"success": False, "error": "Email send failed"}, status=500)

    return JsonResponse({"success": True, "viewer_url": viewer_url})
