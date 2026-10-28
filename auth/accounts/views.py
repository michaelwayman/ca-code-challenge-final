import json

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import keys
from .tokens import token_pair


def _error(status: int, message: str) -> JsonResponse:
    return JsonResponse({"detail": message}, status=status)


@csrf_exempt  # bearer-token API, no cookies involved
@require_POST
def login(request):
    try:
        body = json.loads(request.body)
        username, password = body["username"], body["password"]
    except (ValueError, KeyError, TypeError):
        return _error(400, "Send JSON with username and password.")
    if not isinstance(username, str) or not isinstance(password, str):
        return _error(400, "Send JSON with username and password.")
    # One message for unknown user, wrong password and inactive user alike.
    user = authenticate(request, username=username, password=password)
    if user is None:
        return _error(401, "Invalid credentials.")
    return JsonResponse(token_pair(user))


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
