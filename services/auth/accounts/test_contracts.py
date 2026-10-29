"""Service contracts (R30): claims built by the real issuer pass through the cauth verifier
and validate against docs/contracts/auth/token-claims.schema.json."""

import json
from pathlib import Path

import jwt
from cauth import CLAIMS_VERSION, SUPPORTED_VERSIONS, Role, verify
from django.conf import settings
from django.test import TestCase
from jsonschema import Draft202012Validator

from . import keys
from .models import User
from .tests import KeysDirMixin
from .tokens import issue_access_token
from .wp_import import WP_USER_NAMESPACE, wp_user_uuid

ROOT = Path(settings.BASE_DIR).parent  # /srv in the container, not run on a host
SCHEMA = json.loads((ROOT / "docs" / "contracts" / "auth" / "token-claims.schema.json").read_text())


class TokenClaimsContractTests(KeysDirMixin, TestCase):
    def test_issued_claims_verify_and_match_schema(self):
        for role in Role:
            with self.subTest(role=role):
                user = User.objects.create_user(f"u-{role}", password="pw", role=role)
                token = issue_access_token(user)
                payload = jwt.decode(token, options={"verify_signature": False})
                errors = [e.message for e in Draft202012Validator(SCHEMA).iter_errors(payload)]
                self.assertEqual(errors, [])
                claims = verify(token, keys.jwks())
                self.assertEqual((claims.user_id, claims.role), (str(user.pk), role))

    def test_schema_roles_are_the_cauth_roles(self):
        self.assertEqual(set(SCHEMA["properties"]["role"]["enum"]), {r.value for r in Role})

    def test_schema_versions_are_the_ones_cauth_accepts(self):
        self.assertEqual(set(SCHEMA["properties"]["version"]["enum"]), set(SUPPORTED_VERSIONS))
        self.assertIn(CLAIMS_VERSION, SCHEMA["properties"]["version"]["enum"])


class ReviewerIdContractTests(TestCase):
    def test_wp_user_uuid_follows_the_contract(self):
        contract = json.loads(
            (ROOT / "docs" / "contracts" / "auth" / "reviewer-ids.json").read_text()
        )
        self.assertEqual(str(WP_USER_NAMESPACE), contract["namespace"])
        for example in contract["examples"]:
            self.assertEqual(str(wp_user_uuid(example["wp_user_id"])), example["uuid"])
