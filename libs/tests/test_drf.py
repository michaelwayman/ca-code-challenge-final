import time

import django
import jwt
import pytest
from cauth import EDITOR, READER
from cauth.drf import IsEditor, JWTAuthentication, TokenUser
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from jwt.algorithms import RSAAlgorithm

if not settings.configured:  # bare minimum so DRF imports; no project, no DB
    settings.configure(
        USE_TZ=True,
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
    )
    django.setup()

from rest_framework.response import Response  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402
from rest_framework.views import APIView  # noqa: E402

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_JWK = RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True)
JWKS = {"keys": [{**_JWK, "kid": "k1", "alg": "RS256"}]}


class Auth(JWTAuthentication):
    def get_jwks(self):
        return JWKS


class EditorView(APIView):
    authentication_classes = [Auth]
    permission_classes = [IsEditor]

    def get(self, request):
        return Response({"sub": request.user.id})


def token(role=EDITOR, key=KEY, exp=600, **extra):
    claims = {"sub": "u1", "role": role, "version": 2, "exp": int(time.time()) + exp, **extra}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


def call(auth=None):
    extra = {"HTTP_AUTHORIZATION": auth} if auth else {}
    req = APIRequestFactory().get("/", **extra)
    return EditorView.as_view()(req)


def test_editor_allowed_and_user_from_claims():
    assert call(f"Bearer {token()}").status_code == 200


def test_user_is_token_user_without_db():
    req = APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token()}")
    user, claims = Auth().authenticate(req)
    assert isinstance(user, TokenUser) and user.role == EDITOR and claims["sub"] == "u1"


def test_reader_denied_403():
    assert call(f"Bearer {token(READER)}").status_code == 403


def test_missing_token_401():
    assert call().status_code == 401


@pytest.mark.parametrize(
    "auth",
    ["Bearer garbage", "Bearer", "Basic abc", f"Bearer {token(exp=-10)}"],
)
def test_invalid_token_401(auth):
    assert call(auth).status_code == 401


def test_tampered_token_401():
    head, payload, sig = token(READER).split(".")
    forged = jwt.encode({"sub": "u1", "role": EDITOR, "version": 2}, KEY, algorithm="RS256")
    fp = forged.split(".")[1]
    assert call(f"Bearer {head}.{fp}.{sig}").status_code == 401


def test_wrong_key_401():
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert call(f"Bearer {token(key=other)}").status_code == 401
