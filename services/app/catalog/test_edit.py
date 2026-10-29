import io
import json
import time
from datetime import UTC, datetime, timedelta
from unittest import mock

import jwt
from cauth import Claims, Role
from cryptography.hazmat.primitives.asymmetric import rsa
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from jwt.algorithms import RSAAlgorithm

from config.auth import jwks_cache

from .models import Brand
from .test_api import make_brand, make_review

URL = "/api/brands/acme-insurance/"


def keypair(kid):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = {**RSAAlgorithm.to_jwk(key.public_key(), as_dict=True), "kid": kid, "alg": "RS256"}
    return key, jwk


KEY, JWK = keypair("k1")
NEW_KEY, NEW_JWK = keypair("k2")


def token(role=Role.EDITOR, key=KEY, kid="k1", exp=600):
    now = datetime.now(UTC)
    claims = Claims("u1", role, issued_at=now, expires_at=now + timedelta(seconds=exp))
    return jwt.encode(claims.to_payload(), key, algorithm="RS256", headers={"kid": kid})


def jwks_response(*jwks):
    return io.BytesIO(json.dumps({"keys": list(jwks)}).encode())


def auth_down(*args, **kwargs):
    raise OSError("connection refused")


class EditTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.acme = make_brand("acme-insurance", excerpt="Cheap cover.", description="<p>Long</p>")
        make_review(cls.acme, 5)

    def setUp(self):
        jwks_cache.clear()
        self.addCleanup(jwks_cache.clear)
        self.urlopen = self.patch_urlopen(side_effect=lambda *a, **k: jwks_response(JWK))

    def patch_urlopen(self, **kwargs):
        patcher = mock.patch("config.auth.urllib.request.urlopen", **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def patch(self, data, bearer=None, **extra):
        if bearer:
            extra["HTTP_AUTHORIZATION"] = f"Bearer {bearer}"
        return self.client.patch(URL, data, content_type="application/json", **extra)

    def stored(self):
        return Brand.objects.get(slug="acme-insurance").short_description


class BrandEditTests(EditTestCase):
    def test_editor_updates_short_description(self):
        response = self.patch({"short_description": "Fair prices."}, token())
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["short_description"], "Fair prices.")
        self.assertEqual(response.json()["review_count"], 1)
        self.assertEqual(self.stored(), "Fair prices.")
        listed = self.client.get("/api/brands/").json()["results"][0]
        self.assertEqual(listed["short_description"], "Fair prices.")

    def test_short_description_round_trips_verbatim(self):
        long = " ".join(f"word{i}" for i in range(40))
        for value in ("", long, "  padded  "):
            with self.subTest(value=value):
                response = self.patch({"short_description": value}, token())
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()["short_description"], value)
                self.assertEqual(self.client.get(URL).json()["short_description"], value)
                listed = self.client.get("/api/brands/").json()["results"][0]
                self.assertEqual(listed["short_description"], value)
        # The imported excerpt is left alone for a WP re-import to keep rewriting.
        self.assertEqual(Brand.objects.get(slug="acme-insurance").excerpt, "Cheap cover.")

    def test_patch_loads_the_brand_once(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.patch({"short_description": "Fair prices."}, token())
        self.assertEqual(response.status_code, 200, response.content)
        loads = [q["sql"] for q in queries if 'FROM "catalog_brand"' in q["sql"]]
        self.assertEqual(len(loads), 1, loads)

    def test_reader_is_forbidden(self):
        response = self.patch({"short_description": "x"}, token(role=Role.READER))
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.stored())

    def test_missing_invalid_or_expired_token_is_401(self):
        other_key, _ = keypair("k1")
        cases = {
            "none": self.patch({"short_description": "x"}),
            "garbage": self.patch({"short_description": "x"}, "not-a-jwt"),
            "wrong key": self.patch({"short_description": "x"}, token(key=other_key)),
            "expired": self.patch({"short_description": "x"}, token(exp=-60)),
            "not bearer": self.patch({"short_description": "x"}, HTTP_AUTHORIZATION="Basic YTpi"),
        }
        for name, response in cases.items():
            with self.subTest(name):
                self.assertEqual(response.status_code, 401, response.content)
                self.assertEqual(response["WWW-Authenticate"], "Bearer")
        self.assertIsNone(self.stored())

    def test_only_short_description_is_writable(self):
        response = self.patch({"short_description": "x", "name": "Hacked"}, token())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"name": ["This field is read-only."]})
        response = self.patch({"name": "Hacked"}, token())
        self.assertEqual(response.status_code, 400)
        brand = Brand.objects.get(slug="acme-insurance")
        self.assertEqual((brand.name, brand.short_description), ("Acme Insurance", None))

    def test_put_is_not_allowed(self):
        response = self.client.put(
            URL,
            {"short_description": "x"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token()}",
        )
        self.assertEqual(response.status_code, 405)

    def test_unknown_slug_is_404(self):
        response = self.client.patch(
            "/api/brands/nope/",
            {"short_description": "x"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token()}",
        )
        self.assertEqual(response.status_code, 404)

    def test_get_is_public_and_ignores_tokens(self):
        for headers in ({}, {"HTTP_AUTHORIZATION": "Bearer not-a-jwt"}):
            response = self.client.get(URL, **headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["slug"], "acme-insurance")
        self.urlopen.assert_not_called()


class AuthOutageTests(EditTestCase):
    def test_cached_keys_survive_auth_outage(self):
        self.assertEqual(self.patch({"short_description": "one"}, token()).status_code, 200)
        self.urlopen.side_effect = auth_down
        with mock.patch("config.auth.time.monotonic", return_value=time.monotonic() + 3600):
            # Cache is past max_age and the refetch fails: the stale keys still verify.
            response = self.patch({"short_description": "two"}, token())
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.stored(), "two")
        self.assertEqual(self.client.get(URL).status_code, 200)
        self.assertEqual(self.client.get("/api/brands/").status_code, 200)

    def test_cold_cache_with_auth_down_fails_closed(self):
        self.urlopen.side_effect = auth_down
        response = self.patch({"short_description": "x"}, token())
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(self.stored())
        # The failure is not retried on every request.
        self.patch({"short_description": "x"}, token())
        self.assertEqual(self.urlopen.call_count, 1)

    def test_malformed_jwks_is_not_cached(self):
        for body in ([], {"keys": {}}, {"keys": ["k1"]}, {}):
            with self.subTest(body=body):
                jwks_cache.clear()
                raw = json.dumps(body).encode()
                self.urlopen.side_effect = lambda *a, raw=raw, **k: io.BytesIO(raw)
                response = self.patch({"short_description": "x"}, token())
                self.assertEqual(response.status_code, 503, response.content)
        # Stale good keys win over a malformed refetch.
        jwks_cache.clear()
        self.urlopen.side_effect = lambda *a, **k: jwks_response(JWK)
        self.assertEqual(self.patch({"short_description": "one"}, token()).status_code, 200)
        self.urlopen.side_effect = lambda *a, **k: io.BytesIO(b"[]")
        with mock.patch("config.auth.time.monotonic", return_value=time.monotonic() + 3600):
            response = self.patch({"short_description": "two"}, token())
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.stored(), "two")

    def test_unknown_kid_refetches_rotated_keys(self):
        self.assertEqual(self.patch({"short_description": "one"}, token()).status_code, 200)
        self.urlopen.side_effect = lambda *a, **k: jwks_response(JWK, NEW_JWK)
        response = self.patch({"short_description": "two"}, token(key=NEW_KEY, kid="k2"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.urlopen.call_count, 2)

    def test_unknown_kid_refetch_is_throttled(self):
        self.assertEqual(self.patch({"short_description": "one"}, token()).status_code, 200)
        for _ in range(3):
            response = self.patch({"short_description": "x"}, token(key=NEW_KEY, kid="k9"))
            self.assertEqual(response.status_code, 401)
        self.assertEqual(self.urlopen.call_count, 2)
