"""Log in, then PATCH a brand's short_description. Run via `make patch-brand` (inside the app container)."""

import json
import os
import urllib.error
import urllib.request


def call(url, payload, headers, method):
    request = urllib.request.Request(url, json.dumps(payload).encode(), headers, method=method)
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as error:
        response = error
    return response.status, response.read().decode()


status, body = call(
    "http://auth:8001/auth/login",
    {"username": os.environ["AUTH_USER"], "password": os.environ["AUTH_PASS"]},
    {"Content-Type": "application/json"},
    "POST",
)
if status != 200:
    raise SystemExit(f"login failed: {status} {body} (see README: make admin-password)")
token = json.loads(body)["access_token"]
status, body = call(
    f"http://localhost:8000/api/brands/{os.environ['SLUG']}/",
    {"short_description": os.environ["DESC"]},
    {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    "PATCH",
)
print(f"PATCH {status}\n{body}")
