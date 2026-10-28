"""Print an access token from the auth service. Run via `make token` (inside the auth container)."""

import json
import os
import urllib.request

body = json.dumps(
    {"username": os.environ["AUTH_USER"], "password": os.environ["AUTH_PASS"]}
).encode()
request = urllib.request.Request(
    "http://localhost:8001/auth/login", body, {"Content-Type": "application/json"}
)
try:
    print(json.load(urllib.request.urlopen(request))["access_token"])
except urllib.error.HTTPError as error:
    raise SystemExit(
        f"login failed: {error.code} {error.read().decode()} (see README: make admin-password)"
    )
