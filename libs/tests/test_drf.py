import time

import django
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from shared_auth import Role, public_jwk

if not settings.configured:  # bare minimum so DRF imports; no project, no DB
    settings.configure(
        USE_TZ=True,
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
    )
    django.setup()

from rest_framework.response import Response  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402
from rest_framework.views import APIView  # noqa: E402
from shared_auth.drf import IsEditor, JWTAuthentication, TokenUser  # noqa: E402

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
JWKS = {"keys": [public_jwk(KEY.public_key(), "k1")]}


class StaticKeys:
    def __init__(self, *jwks):
        self.sets = list(jwks)
        self.refreshes = 0

    def get(self):
        return self.sets[0]

    def refresh(self):
        self.refreshes += 1
        if len(self.sets) == 1:
            return False
        self.sets.pop(0)
        return True


class Auth(JWTAuthentication):
    key_source = StaticKeys(JWKS)


class EditorView(APIView):
    authentication_classes = [Auth]
    permission_classes = [IsEditor]

    def get(self, request):
        return Response({"sub": request.user.id})


def token(role=Role.EDITOR, key=KEY, exp=600, kid="k1", **extra):
    claims = {"sub": "u1", "role": role, "version": 2, "exp": int(time.time()) + exp, **extra}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


def call(auth=None):
    extra = {"HTTP_AUTHORIZATION": auth} if auth else {}
    req = APIRequestFactory().get("/", **extra)
    return EditorView.as_view()(req)


def test_editor_allowed_and_user_from_claims():
    assert call(f"Bearer {token()}").status_code == 200


def test_user_is_token_user_without_db():
    req = APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token()}")
    user, claims = Auth().authenticate(req)
    assert isinstance(user, TokenUser) and user.role == Role.EDITOR and claims.sub == "u1"


def test_reader_denied_403():
    assert call(f"Bearer {token(Role.READER)}").status_code == 403


def test_missing_token_401():
    assert call().status_code == 401


@pytest.mark.parametrize(
    "auth",
    ["Bearer garbage", "Bearer", "Basic abc", f"Bearer {token(exp=-10)}"],
)
def test_invalid_token_401(auth):
    assert call(auth).status_code == 401


def test_tampered_token_401():
    head, payload, sig = token(Role.READER).split(".")
    forged = jwt.encode({"sub": "u1", "role": Role.EDITOR, "version": 2}, KEY, algorithm="RS256")
    fp = forged.split(".")[1]
    assert call(f"Bearer {head}.{fp}.{sig}").status_code == 401


def test_wrong_key_401():
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert call(f"Bearer {token(key=other)}").status_code == 401


def test_unknown_kid_refreshes_keys_once_and_retries():
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rotated = {"keys": [*JWKS["keys"], public_jwk(other.public_key(), "k2")]}
    keys = StaticKeys(JWKS, rotated)
    req = APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token(key=other, kid='k2')}")
    auth = Auth()
    auth.key_source = keys
    user, _ = auth.authenticate(req)
    assert user.id == "u1" and keys.refreshes == 1


def test_unknown_kid_without_new_keys_401():
    assert call(f"Bearer {token(kid='k9')}").status_code == 401
