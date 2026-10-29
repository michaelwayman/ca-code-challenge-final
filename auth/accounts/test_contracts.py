"""Service contracts (R30): claims built by the real issuer pass through the cauth verifier
and validate against contracts/token-claims.schema.json."""

import json
from pathlib import Path

from cauth import CLAIMS_VERSION, EDITOR, READER, SUPPORTED_VERSIONS, verify
from django.conf import settings
from django.test import TestCase
from jsonschema import Draft202012Validator

from . import keys
from .models import User
from .tests import KeysDirMixin
from .tokens import issue_access_token

ROOT = Path(settings.BASE_DIR).parent  # /srv in the container, the repo root on a host
SCHEMA = json.loads((ROOT / "contracts" / "token-claims.schema.json").read_text())


class TokenClaimsContractTests(KeysDirMixin, TestCase):
    def test_issued_claims_verify_and_match_schema(self):
        for role in (READER, EDITOR):
            with self.subTest(role=role):
                user = User.objects.create_user(f"u-{role}", password="pw", role=role)
                claims = verify(issue_access_token(user), keys.jwks())
                errors = [e.message for e in Draft202012Validator(SCHEMA).iter_errors(claims)]
                self.assertEqual(errors, [])
                self.assertEqual((claims["sub"], claims["role"]), (str(user.pk), role))

    def test_schema_versions_are_the_ones_cauth_accepts(self):
        self.assertEqual(set(SCHEMA["properties"]["version"]["enum"]), set(SUPPORTED_VERSIONS))
        self.assertIn(CLAIMS_VERSION, SCHEMA["properties"]["version"]["enum"])
