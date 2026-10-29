import time

import jwt
import pytest
from cauth import BadSignature, ExpiredToken, MalformedToken, UnknownKid, verify
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_for(key, kid="k1"):
    jwk = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    return {"keys": [{**jwk, "kid": kid, "alg": "RS256", "use": "sig"}]}


def sign(key, kid="k1", **claims):
    claims.setdefault("exp", int(time.time()) + 600)
    claims.setdefault("sub", "u1")
    claims.setdefault("role", "editor")
    claims.setdefault("version", 1)
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


KEY = make_key()
JWKS = jwks_for(KEY)


def test_valid_returns_claims_with_version():
    claims = verify(sign(KEY), JWKS)
    assert claims["sub"] == "u1"
    assert claims["role"] == "editor"
    assert claims["version"] == 1


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
    from cauth import CLAIMS_VERSION

    for v in (CLAIMS_VERSION, CLAIMS_VERSION - 1):
        assert verify(sign(KEY, version=v), JWKS)["version"] == v


@pytest.mark.parametrize("v", [0, 3, None, True, 2.0, [2], {"a": 1}, "2"])
def test_other_versions_rejected(v):
    from cauth import UnsupportedVersion

    with pytest.raises(UnsupportedVersion):
        verify(sign(KEY, version=v), JWKS)
