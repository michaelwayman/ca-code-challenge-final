import time
from datetime import UTC, datetime

import jwt
import pytest
from cauth import (
    CLAIMS_VERSION,
    BadSignature,
    Claims,
    ExpiredToken,
    MalformedToken,
    Role,
    UnknownKid,
    UnsupportedVersion,
    verify,
)
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_for(key, kid="k1"):
    jwk = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    return {"keys": [{**jwk, "kid": kid, "alg": "RS256", "use": "sig"}]}


def payload(**overrides):
    now = int(time.time())
    base = {"sub": "u1", "role": "editor", "iat": now, "exp": now + 600, "version": 1}
    return {k: v for k, v in {**base, **overrides}.items() if v is not ...}  # `...` drops a claim


def sign(key, kid="k1", **overrides):
    return jwt.encode(payload(**overrides), key, algorithm="RS256", headers={"kid": kid})


KEY = make_key()
JWKS = jwks_for(KEY)


def test_valid_token_returns_typed_claims():
    claims = verify(sign(KEY), JWKS)
    assert isinstance(claims, Claims)
    assert claims.user_id == "u1"
    assert claims.role is Role.EDITOR
    assert claims.version == 1
    assert claims.expires_at > claims.issued_at


def test_claims_round_trip_through_the_payload():
    now = datetime.now(UTC).replace(microsecond=0)
    claims = Claims("u1", Role.READER, issued_at=now, expires_at=now.replace(year=now.year + 1))
    assert claims.version == CLAIMS_VERSION
    assert Claims.from_payload(claims.to_payload()) == claims


def test_payload_uses_the_jwt_field_names():
    now = datetime.fromtimestamp(1_700_000_000, UTC)
    claims = Claims("u1", Role.EDITOR, issued_at=now, expires_at=now)
    assert claims.to_payload() == {
        "sub": "u1",
        "role": "editor",
        "iat": 1_700_000_000,
        "exp": 1_700_000_000,
        "version": CLAIMS_VERSION,
    }


def test_role_is_a_string_enum():
    assert Role.EDITOR == "editor"
    assert [r.value for r in Role] == ["reader", "editor"]


def test_expired():
    with pytest.raises(ExpiredToken):
        verify(sign(KEY, exp=int(time.time()) - 10), JWKS)


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


def test_errors_are_distinct():
    classes = {ExpiredToken, BadSignature, UnknownKid, MalformedToken}
    assert len(classes) == 4


def test_versions_n_and_n_minus_1_accepted():
    for v in (CLAIMS_VERSION, CLAIMS_VERSION - 1):
        assert verify(sign(KEY, version=v), JWKS).version == v


@pytest.mark.parametrize("v", [0, 3, None, True, 2.0, [2], {"a": 1}, "2"])
def test_other_versions_rejected(v):
    with pytest.raises(UnsupportedVersion):
        verify(sign(KEY, version=v), JWKS)


@pytest.mark.parametrize("missing", ["exp", "iat", "sub", "role"])
def test_required_claims_must_be_present(missing):
    with pytest.raises(MalformedToken):
        verify(sign(KEY, **{missing: ...}), JWKS)


@pytest.mark.parametrize("role", ["admin", "", None, 7, ["editor"]])
def test_unknown_role_rejected(role):
    with pytest.raises(MalformedToken):
        verify(sign(KEY, role=role), JWKS)
