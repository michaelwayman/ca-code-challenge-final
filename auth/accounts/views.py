import json

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import keys
from .tokens import access_token_response, find_live_refresh_token, revoke, token_pair


def _error(status: int, message: str) -> JsonResponse:
    return JsonResponse({"detail": message}, status=status)


def _string_fields(request, *names):
    """The named string fields of a JSON body, or None if any is missing or not a string."""
    try:
        body = json.loads(request.body)
        values = [body[name] for name in names]
    except (ValueError, KeyError, TypeError):
        return None
    return values if all(isinstance(v, str) for v in values) else None


@csrf_exempt  # bearer-token API, no cookies involved
@require_POST
def login(request):
    fields = _string_fields(request, "username", "password")
    if fields is None:
        return _error(400, "Send JSON with username and password.")
    username, password = fields
    # One message for unknown user, wrong password and inactive user alike.
    user = authenticate(request, username=username, password=password)
    if user is None:
        return _error(401, "Invalid credentials.")
    return JsonResponse(token_pair(user))


@csrf_exempt
@require_POST
def refresh(request):
    fields = _string_fields(request, "refresh_token")
    if fields is None:
        return _error(400, "Send JSON with refresh_token.")
    # Unknown, expired, revoked and inactive-user tokens share one answer.
    token = find_live_refresh_token(fields[0])
    if token is None:
        return _error(401, "Invalid refresh token.")
    return JsonResponse(access_token_response(token.user))


@csrf_exempt
@require_POST
def logout(request):
    fields = _string_fields(request, "refresh_token")
    if fields is None:
        return _error(400, "Send JSON with refresh_token.")
    # 204 whether or not the token existed, so logout is not a token oracle.
    revoke(fields[0])
    return HttpResponse(status=204)


@require_GET
def jwks(request):
    response = JsonResponse(keys.jwks())
    response["Cache-Control"] = f"public, max-age={settings.JWKS_MAX_AGE}"
    return response


@require_GET
def healthz(request):
    try:
        connection.ensure_connection()
    except Exception:
        return _error(503, "database unavailable")
    return JsonResponse({"status": "ok"})
