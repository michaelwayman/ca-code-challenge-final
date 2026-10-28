import json
import tempfile
import time

import jwt
from cauth import CLAIMS_VERSION, EDITOR, verify
from django.test import TestCase, override_settings

from . import keys
from .models import RefreshToken, User


class KeysDirMixin:
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        override = override_settings(AUTH_KEYS_DIR=tmp.name)
        override.enable()
        self.addCleanup(override.disable)
        keys.add_key()

    def login(self, username="ed", password="pw-correct"):
        return self.client.post(
            "/auth/login",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )

    def jwks(self):
        return self.client.get("/.well-known/jwks.json").json()


class LoginTests(KeysDirMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("ed", password="pw-correct", role=EDITOR)

    def test_valid_credentials_return_rs256_access_and_refresh_token(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        header = jwt.get_unverified_header(body["access_token"])
        self.assertEqual(header["alg"], "RS256")
        self.assertEqual(header["kid"], keys.active_key().kid)
        self.assertEqual(body["token_type"], "Bearer")
        self.assertEqual(body["expires_in"], 600)
        self.assertTrue(body["refresh_token"])

    def test_access_token_claims_verify_with_shared_library(self):
        claims = verify(self.login().json()["access_token"], self.jwks())
        self.assertEqual(claims["sub"], str(self.user.pk))
        self.assertEqual(claims["role"], EDITOR)
        self.assertEqual(claims["version"], CLAIMS_VERSION)
        self.assertAlmostEqual(claims["exp"] - time.time(), 600, delta=5)

    def test_refresh_token_stored_hashed(self):
        raw = self.login().json()["refresh_token"]
        stored = RefreshToken.objects.get(user=self.user)
        self.assertNotEqual(stored.token_hash, raw)
        self.assertEqual(stored.token_hash, RefreshToken.hash(raw))

    def test_wrong_password_and_unknown_user_are_indistinguishable(self):
        wrong_password = self.login(password="nope")
        unknown_user = self.login(username="nobody")
        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_user.status_code, 401)
        self.assertEqual(wrong_password.json(), unknown_user.json())

    def test_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.login().status_code, 401)

    def test_malformed_body_is_400(self):
        response = self.client.post("/auth/login", data="nope", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get("/auth/login").status_code, 405)


class JWKSTests(KeysDirMixin, TestCase):
    def test_public_key_set_with_kid_and_no_private_material(self):
        response = self.client.get("/.well-known/jwks.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("max-age=", response["Cache-Control"])
        [jwk] = response.json()["keys"]
        self.assertEqual(jwk["kid"], keys.active_key().kid)
        self.assertEqual(jwk["kty"], "RSA")
        self.assertFalse({"d", "p", "q", "dp", "dq", "qi"} & jwk.keys())

    def test_second_key_keeps_old_tokens_verifiable(self):
        User.objects.create_user("ed", password="pw-correct")
        old_token = self.login().json()["access_token"]
        old_kid = jwt.get_unverified_header(old_token)["kid"]

        new_kid = keys.add_key()
        new_token = self.login().json()["access_token"]

        self.assertEqual(jwt.get_unverified_header(new_token)["kid"], new_kid)
        jwks = self.jwks()
        self.assertEqual({k["kid"] for k in jwks["keys"]}, {old_kid, new_kid})
        verify(old_token, jwks)
        verify(new_token, jwks)


class HealthTests(TestCase):
    def test_healthz(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
