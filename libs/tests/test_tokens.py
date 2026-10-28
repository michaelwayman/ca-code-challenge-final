import time
from datetime import timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from shared_auth import (
    ACCEPTED_VERSIONS,
    ISSUED_VERSION,
    BadSignature,
    ExpiredToken,
    MalformedToken,
    UnknownKid,
    UnsupportedVersion,
    issue,
    public_jwk,
    verify,
)


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def sign(key, kid="k1", **claims):
    claims.setdefault("exp", int(time.time()) + 600)
    claims.setdefault("sub", "u1")
    claims.setdefault("role", "editor")
    claims.setdefault("version", 1)
    claims = {name: value for name, value in claims.items() if value is not ...}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


KEY = make_key()
JWKS = {"keys": [public_jwk(KEY.public_key(), "k1")]}


def test_valid_returns_claims_with_version():
    claims = verify(sign(KEY), JWKS)
    assert (claims.sub, claims.role, claims.version) == ("u1", "editor", 1)


def test_issue_round_trips_through_verify():
    token = issue(sub="u7", role="reader", private_key=KEY, kid="k1", ttl=timedelta(minutes=10))
    claims = verify(token, JWKS)
    assert (claims.sub, claims.role, claims.version) == ("u7", "reader", ISSUED_VERSION)
    assert jwt.get_unverified_header(token)["kid"] == "k1"


def test_public_jwk_shape():
    expected = {"kid": "k1", "alg": "RS256", "use": "sig", "kty": "RSA"}
    assert expected.items() <= JWKS["keys"][0].items()


def test_expired():
    with pytest.raises(ExpiredToken):
        verify(sign(KEY, exp=int(time.time()) - 10), JWKS)


@pytest.mark.parametrize("claim", ["exp", "sub", "role"])
def test_required_claim_missing(claim):
    with pytest.raises(MalformedToken):
        verify(sign(KEY, **{claim: ...}), JWKS)


def test_bad_signature():
    with pytest.raises(BadSignature):
        verify(sign(make_key()), JWKS)


def test_unknown_kid():
    with pytest.raises(UnknownKid):
        verify(sign(KEY, kid="other"), JWKS)


@pytest.mark.parametrize("token", ["", "abc", "a.b.c"])
def test_malformed(token):
    with pytest.raises(MalformedToken):
        verify(token, JWKS)


def test_issued_version_is_accepted():
    assert ISSUED_VERSION in ACCEPTED_VERSIONS


@pytest.mark.parametrize("v", sorted(ACCEPTED_VERSIONS))
def test_accepted_versions_verify(v):
    assert verify(sign(KEY, version=v), JWKS).version == v


@pytest.mark.parametrize("v", [0, 3, None, True, 2.0, [2], {"a": 1}, "2", ...])
def test_other_versions_rejected(v):
    with pytest.raises(UnsupportedVersion):
        verify(sign(KEY, version=v), JWKS)
