import json
import tempfile
import time
from datetime import UTC, datetime
from io import StringIO
from unittest import mock

import jwt
from cauth import CLAIMS_VERSION, EDITOR, READER, deterministic_uuid, verify
from django.contrib.auth.hashers import get_hasher
from django.core.management import call_command
from django.test import TestCase, override_settings

from . import keys
from .hashers import WordPressPasswordHasher
from .models import RefreshToken, User
from .wp_import import WPUser, import_users


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


class RefreshTests(KeysDirMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("ed", password="pw-correct", role=EDITOR)
        self.refresh_token = self.login().json()["refresh_token"]

    def post(self, path, body):
        return self.client.post(path, data=json.dumps(body), content_type="application/json")

    def refresh(self, token=None):
        return self.post("/auth/refresh", {"refresh_token": token or self.refresh_token})

    def logout(self, token=None):
        return self.post("/auth/logout", {"refresh_token": token or self.refresh_token})

    def test_refresh_returns_new_access_token(self):
        response = self.refresh()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["token_type"], "Bearer")
        self.assertEqual(body["expires_in"], 600)
        claims = verify(body["access_token"], self.jwks())
        self.assertEqual(claims["sub"], str(self.user.pk))
        self.assertEqual(claims["role"], EDITOR)

    def test_demoted_user_gets_reader_role_on_next_refresh(self):
        self.user.role = READER
        self.user.save()
        claims = verify(self.refresh().json()["access_token"], self.jwks())
        self.assertEqual(claims["role"], READER)

    def test_logged_out_token_is_401(self):
        self.assertEqual(self.logout().status_code, 204)
        self.assertEqual(self.refresh().status_code, 401)

    def test_logout_is_idempotent_and_does_not_reveal_unknown_tokens(self):
        self.logout()
        self.assertEqual(self.logout().status_code, 204)
        self.assertEqual(self.logout("nope").status_code, 204)

    def test_revoked_token_is_401(self):
        RefreshToken.objects.update(revoked_at=datetime.now(UTC))
        self.assertEqual(self.refresh().status_code, 401)

    def test_expired_token_is_401(self):
        RefreshToken.objects.update(expires_at=datetime.now(UTC))
        self.assertEqual(self.refresh().status_code, 401)

    def test_unknown_token_is_401(self):
        self.assertEqual(self.refresh("not-a-token").status_code, 401)

    def test_inactive_user_is_401(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.refresh().status_code, 401)

    def test_malformed_body_is_400(self):
        self.assertEqual(self.post("/auth/refresh", {"token": "x"}).status_code, 400)
        self.assertEqual(self.post("/auth/logout", {"refresh_token": 1}).status_code, 400)


class AdminTests(TestCase):
    def setUp(self):
        self.operator = User.objects.create_superuser("op", password="pw-op")
        self.user = User.objects.create_user("ed", password="pw-correct", role=EDITOR)
        self.client.force_login(self.operator)

    def test_operator_changes_role_in_admin(self):
        url = f"/admin/accounts/user/{self.user.pk}/change/"
        page = self.client.get(url)
        self.assertContains(page, 'name="role"')
        response = self.client.post(
            url,
            {
                "username": "ed",
                "is_active": "on",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "00:00:00",
                "role": READER,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, READER)

    def test_operator_revokes_refresh_tokens_in_admin(self):
        token = RefreshToken.objects.create(
            user=self.user, token_hash="x" * 64, expires_at=datetime.now(UTC)
        )
        self.client.post(
            "/admin/accounts/refreshtoken/",
            {"action": "revoke", "_selected_action": [token.pk]},
        )
        token.refresh_from_db()
        self.assertIsNotNone(token.revoked_at)


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

    def test_key_files_are_parsed_once_until_the_ring_changes(self):
        keys.load_keys()
        with mock.patch.object(
            keys.serialization,
            "load_pem_private_key",
            wraps=keys.serialization.load_pem_private_key,
        ) as parse:
            keys.load_keys()
            keys.load_keys()
            self.assertEqual(parse.call_count, 0)
            keys.add_key()
            self.assertEqual(len(keys.load_keys()), 2)
            self.assertEqual(parse.call_count, 2)


# Generated with WordPress 6.9's own code (class-phpass.php, wp_hash_password) for "hunter2".
WP_PHPASS = "$P$BVRYel7YxFGYlqMhNxO4gy9IIcajYw1"
WP_BCRYPT = "$wp$2y$10$se4HljuFe3P3I/kMcXxCFe6uy59bSdwNZ4H/s6qIBh1wBKMtsjIXm"


class WordPressHasherTests(TestCase):
    def setUp(self):
        self.hasher = WordPressPasswordHasher()

    def test_phpass_portable_hash(self):
        self.assertTrue(self.hasher.verify("hunter2", WP_PHPASS))
        self.assertFalse(self.hasher.verify("hunter3", WP_PHPASS))

    def test_phpbb_h_prefix_is_same_algorithm(self):
        self.assertTrue(self.hasher.verify("hunter2", "$H$" + WP_PHPASS[3:]))

    def test_wp_bcrypt_hash(self):
        self.assertTrue(self.hasher.verify("hunter2", WP_BCRYPT))
        self.assertFalse(self.hasher.verify("hunter3", WP_BCRYPT))

    def test_registered_with_django(self):
        self.assertIsInstance(get_hasher("wordpress"), WordPressPasswordHasher)

    def test_malformed_hashes_rejected(self):
        for encoded in ("$P$", "$P$!aaaaaaaa", "$wp$2y$garbage", "plain"):
            self.assertFalse(self.hasher.verify("hunter2", encoded))


class WordPressLoginTests(KeysDirMixin, TestCase):
    def test_each_wp_format_logs_in_then_rehashes_to_django_default(self):
        for username, encoded in (("phpass", WP_PHPASS), ("bcrypt", WP_BCRYPT)):
            with self.subTest(username):
                user = User.objects.create(username=username, password=encoded)
                response = self.login(username, "hunter2")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["access_token"])
                user.refresh_from_db()
                self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
                self.assertEqual(self.login(username, "hunter2").status_code, 200)

    def test_wrong_password_is_401_and_hash_kept(self):
        User.objects.create(username="wp", password=WP_BCRYPT)
        self.assertEqual(self.login("wp", "hunter3").status_code, 401)
        self.assertEqual(User.objects.get(username="wp").password, WP_BCRYPT)


def wp_user(id, login="sarah_k", capabilities='a:1:{s:10:"subscriber";b:1;}', **kw):
    return WPUser(
        id=id,
        login=login,
        email=kw.get("email", f"{login}@example.com"),
        password_hash=kw.get("password_hash", WP_BCRYPT),
        registered=datetime(2026, 5, 19, 20, 28, 55),
        capabilities=capabilities,
    )


class ImportWPUsersTests(KeysDirMixin, TestCase):
    rows = [
        wp_user(1, "admin", 'a:1:{s:13:"administrator";b:1;}', password_hash=WP_PHPASS),
        wp_user(2, "sarah_k"),
        wp_user(3, "edna", 'a:1:{s:6:"editor";b:1;}'),
        wp_user(4, "norole", ""),
    ]

    def test_one_user_per_row_with_deterministic_pk_and_mapped_role(self):
        self.assertEqual(import_users(self.rows), {"created": 4, "updated": 0})
        roles = {u.username: u.role for u in User.objects.all()}
        self.assertEqual(
            roles, {"admin": EDITOR, "sarah_k": READER, "edna": EDITOR, "norole": READER}
        )
        admin = User.objects.get(username="admin")
        self.assertEqual(admin.pk, deterministic_uuid("wp_user", 1))
        self.assertEqual(admin.password, WP_PHPASS)
        self.assertEqual(admin.date_joined, datetime(2026, 5, 19, 20, 28, 55, tzinfo=UTC))

    def test_no_wp_user_id_column(self):
        columns = {f.column for f in User._meta.get_fields() if hasattr(f, "column")}
        self.assertFalse({c for c in columns if "wp" in c})

    def test_rerun_keeps_count_and_password_hashes(self):
        import_users(self.rows)
        self.assertEqual(import_users(self.rows), {"created": 0, "updated": 4})
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(User.objects.get(username="sarah_k").password, WP_BCRYPT)

    def test_rerun_does_not_revert_rehash_or_role_change(self):
        import_users(self.rows)
        self.assertEqual(self.login("sarah_k", "hunter2").status_code, 200)
        User.objects.filter(username="sarah_k").update(role=EDITOR)
        rehashed = User.objects.get(username="sarah_k").password

        import_users(self.rows)
        sarah = User.objects.get(username="sarah_k")
        self.assertEqual(sarah.password, rehashed)
        self.assertEqual(sarah.role, EDITOR)

    def test_rerun_refreshes_profile_fields(self):
        import_users(self.rows)
        import_users([wp_user(2, "sarah_k", email="new@example.com")])
        self.assertEqual(User.objects.get(username="sarah_k").email, "new@example.com")

    def test_rerun_takes_login_freed_by_later_row(self):
        import_users(self.rows)
        # WP 1 takes sarah_k, which WP 2 gives up further down the loop; 3 and 4 swap.
        renamed = [
            wp_user(1, "sarah_k"),
            wp_user(2, "sarah_new"),
            wp_user(3, "norole"),
            wp_user(4, "edna"),
        ]
        self.assertEqual(import_users(renamed), {"created": 0, "updated": 4})
        usernames = {u.pk: u.username for u in User.objects.all()}
        self.assertEqual(
            usernames, {deterministic_uuid("wp_user", wp.id): wp.login for wp in renamed}
        )

    def test_command_reads_source_and_prints_counts(self):
        out = StringIO()
        with mock.patch(
            "accounts.management.commands.import_wp_users.fetch_wp_users",
            return_value=self.rows,
        ):
            call_command("import_wp_users", stdout=out)
        self.assertIn("created 4, updated 0", out.getvalue())


class HealthTests(TestCase):
    def test_healthz(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
