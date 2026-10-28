"""Log in to the auth service, then print the token or PATCH a brand. Runs in the app container:

make token         -> python - token        (AUTH_USER, AUTH_PASS)
make patch-brand   -> python - patch-brand  (also SLUG, DESC)
"""

import json
import os
import sys
import urllib.error
import urllib.request

AUTH_URL = os.environ.get("AUTH_URL", "http://auth:8001")
APP_URL = os.environ.get("APP_URL", "http://localhost:8000")


def call(method, url, payload, headers=None):
    """(status, body) for a JSON request; HTTP errors are returned, not raised."""
    headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, json.dumps(payload).encode(), headers, method=method)
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as error:
        response = error
    return response.status, response.read().decode()


def login():
    credentials = {"username": os.environ["AUTH_USER"], "password": os.environ["AUTH_PASS"]}
    try:
        status, body = call("POST", f"{AUTH_URL}/auth/login", credentials)
    except urllib.error.URLError as error:
        raise SystemExit(f"auth service unreachable at {AUTH_URL}: {error.reason}") from None
    if status != 200:
        raise SystemExit(f"login failed: {status} {body} (see README: make admin-password)")
    return json.loads(body)["access_token"]


def patch_brand(token):
    status, body = call(
        "PATCH",
        f"{APP_URL}/api/brands/{os.environ['SLUG']}/",
        {"short_description": os.environ["DESC"]},
        {"Authorization": f"Bearer {token}"},
    )
    print(f"PATCH {status}\n{body}")


command = sys.argv[1] if len(sys.argv) > 1 else ""
if command == "token":
    print(login())
elif command == "patch-brand":
    patch_brand(login())
else:
    raise SystemExit("usage: api_client.py token|patch-brand")
