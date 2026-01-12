import json
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseForbidden
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


def card_viewer(request, token):
    link = get_object_or_404(CardLink, token=token)
    return render(request, "studio_bridge/card_viewer.html", {"link": link})


@csrf_exempt
@require_http_methods(["POST"])
def send_card_email_api(request):
    expected = (getattr(settings, "STUDIO_API_KEY", "") or "").strip()
    provided = (request.META.get("HTTP_X_STUDIO_KEY", "") or "").strip()
    if not expected or provided != expected:
        return HttpResponseForbidden("Forbidden")

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

    # Safety: only allow expected destinations (prevents endpoint abuse)
    allowed = ("caffeine.xyz", "ic0.app", "mintkit.co.uk")
    if not any(d in open_url for d in allowed):
        return JsonResponse({"success": False, "error": "open_url domain not allowed"}, status=400)

    link = CardLink.objects.create(
        nft_id=nft_id,
        open_url=open_url,
        image_url=image_url,
        recipient_email=recipient_email,
    )

    viewer_url = f"{(settings.SITE_URL or '').rstrip('/')}/v/{link.token}/"

    sent = send_card_received_email(to_email=recipient_email, viewer_url=viewer_url, request=None)
    if not sent:
        return JsonResponse({"success": False, "error": "Email send failed"}, status=500)

    return JsonResponse({"success": True, "viewer_url": viewer_url})
