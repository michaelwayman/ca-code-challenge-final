"""Service contracts (R30): the brands API schema in docs/contracts/ against the real responses,
the frontend fixture, and the constants api.py and frontend/src/lib/constants.js each define."""

import json
import re
from pathlib import Path

from cauth import Role
from django.conf import settings
from django.test import TestCase
from jsonschema import Draft202012Validator

from . import api
from .test_api import make_brand
from .test_edit import JWK, EditTestCase, jwks_response, token
from .wp_import import WP_USER_NAMESPACE, wp_user_uuid

ROOT = Path(settings.BASE_DIR).parent  # /srv in the container, not run on a host
SPEC = json.loads((ROOT / "docs" / "contracts" / "app" / "brands-api.openapi.json").read_text())
URL_JS = (ROOT / "frontend" / "src" / "lib" / "constants.js").read_text()
FIXTURE = json.loads((ROOT / "frontend" / "src" / "fixtures" / "brands-page.json").read_text())


def validator(name):
    """Validate against components.schemas[name]; $refs resolve inside the same document."""
    return Draft202012Validator(
        {"$ref": f"#/components/schemas/{name}", "components": SPEC["components"]}
    )


def response_schema(path, method, status):
    ref = SPEC["paths"][path][method]["responses"][status]["content"]["application/json"]["schema"]
    return ref["$ref"].rsplit("/", 1)[1]


class ApiContractTests(EditTestCase):
    def setUp(self):
        super().setUp()
        make_brand("bolt-bank")  # no industry, no reviews: the null branches
        self.urlopen.side_effect = lambda *a, **k: jwks_response(JWK)

    def assert_valid(self, name, body):
        errors = [e.message for e in validator(name).iter_errors(body)]
        self.assertEqual(errors, [], body)

    def test_listing_matches_schema(self):
        response = self.client.get("/api/brands/", {"page_size": 1})
        self.assertEqual(response.status_code, 200)
        self.assert_valid(response_schema("/api/brands/", "get", "200"), response.json())
        self.assertIsNotNone(response.json()["next"])

    def test_listing_with_null_fields_matches_schema(self):
        body = self.client.get("/api/brands/", {"ordering": "-review_count"}).json()
        self.assert_valid("BrandPage", body)
        self.assertIsNone(body["results"][-1]["top_review"])

    def test_brand_and_patch_match_schema(self):
        got = self.client.get("/api/brands/acme-insurance/")
        self.assert_valid(response_schema("/api/brands/{slug}/", "get", "200"), got.json())
        patched = self.client.patch(
            "/api/brands/acme-insurance/",
            {"short_description": "Fair prices."},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token(role=Role.EDITOR)}",
        )
        self.assertEqual(patched.status_code, 200)
        self.assert_valid(response_schema("/api/brands/{slug}/", "patch", "200"), patched.json())

    def test_error_bodies_match_schema(self):
        patch = "/api/brands/{slug}/", "patch"
        cases = {
            "400": ({"name": "x"}, token()),
            "401": ({"short_description": "x"}, None),
            "403": ({"short_description": "x"}, token(role=Role.READER)),
        }
        for status, (data, bearer) in cases.items():
            with self.subTest(status):
                extra = {"HTTP_AUTHORIZATION": f"Bearer {bearer}"} if bearer else {}
                response = self.client.patch(
                    "/api/brands/acme-insurance/", data, content_type="application/json", **extra
                )
                self.assertEqual(response.status_code, int(status), response.content)
                self.assert_valid(response_schema(*patch, status), response.json())
        missing = self.client.get("/api/brands/nope/")
        self.assertEqual(missing.status_code, 404)
        self.assert_valid(response_schema("/api/brands/{slug}/", "get", "404"), missing.json())
        past_end = self.client.get("/api/brands/", {"page": 99})
        self.assertEqual(past_end.status_code, 404)
        self.assert_valid(response_schema("/api/brands/", "get", "404"), past_end.json())

    def test_documented_params_match_the_code(self):
        listed = SPEC["paths"]["/api/brands/"]["get"]["parameters"]
        params = {p["name"]: p["schema"] for p in listed}
        ordering = params["ordering"]
        self.assertEqual(ordering["default"], api.DEFAULT_ORDERING)
        self.assertEqual(
            set(ordering["enum"]),
            {sign + key for key in api.ORDERINGS for sign in ("", "-")},
        )
        self.assertEqual(params["page_size"]["default"], api.BrandPagination.page_size)
        self.assertEqual(params["page_size"]["maximum"], api.BrandPagination.max_page_size)


class FrontendContractTests(EditTestCase):
    def test_fixture_matches_schema(self):
        errors = [e.message for e in validator("BrandPage").iter_errors(FIXTURE)]
        self.assertEqual(errors, [])

    def test_frontend_constants_agree_with_api(self):
        page_size = int(re.search(r"PAGE_SIZE = (\d+);", URL_JS).group(1))
        default = re.search(r'DEFAULT_ORDERING = "([^"]+)"', URL_JS).group(1)
        offered = set(re.findall(r'\{ value: "([^"]+)"', URL_JS))
        self.assertEqual(default, api.DEFAULT_ORDERING)
        self.assertLessEqual(page_size, api.BrandPagination.max_page_size)
        self.assertEqual(offered, {s + k for k in api.ORDERINGS for s in ("", "-")})


class ReviewerIdContractTests(TestCase):
    def test_wp_user_uuid_follows_the_contract(self):
        contract = json.loads(
            (ROOT / "docs" / "contracts" / "auth" / "reviewer-ids.json").read_text()
        )
        self.assertEqual(str(WP_USER_NAMESPACE), contract["namespace"])
        for example in contract["examples"]:
            self.assertEqual(str(wp_user_uuid(example["wp_user_id"])), example["uuid"])
