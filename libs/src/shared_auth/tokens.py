"""The access-token contract between the auth service (issuer) and its consumers.

Both sides import this module, so the claim names, the algorithm, the JWKS entry shape and
the claims versions are defined once.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from jwt.algorithms import RSAAlgorithm

from .errors import BadSignature, ExpiredToken, MalformedToken, UnknownKid, UnsupportedVersion

ALGORITHM = "RS256"

# Releasing a breaking claims change takes three edits, each its own release:
#   1. expand:   add the new version to ACCEPTED_VERSIONS; deploy consumers first
#   2. switch:   set ISSUED_VERSION to it; deploy the auth service
#   3. contract: once old tokens have expired, drop the old version from ACCEPTED_VERSIONS
ISSUED_VERSION = 2
ACCEPTED_VERSIONS = frozenset({1, 2})

REQUIRED_CLAIMS = ["exp", "sub", "role"]


@dataclass(frozen=True)
class Claims:
    sub: str
    role: str
    version: int
    exp: int


def issue(*, sub: str, role: str, private_key, kid: str, ttl: timedelta) -> str:
    """Sign an access token for `sub` with `role`, valid for `ttl`."""
    now = datetime.now(UTC)
    claims = {"sub": sub, "role": role, "iat": now, "exp": now + ttl, "version": ISSUED_VERSION}
    return jwt.encode(claims, private_key, algorithm=ALGORITHM, headers={"kid": kid})


def public_jwk(public_key, kid: str) -> dict:
    """One JWKS entry for `public_key`, as the auth service publishes it."""
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    return {**jwk, "kid": kid, "alg": ALGORITHM, "use": "sig"}


def verify(token: str, jwks: dict) -> Claims:
    """Return the claims of a valid token, or raise a TokenError subclass."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise MalformedToken(str(exc)) from exc
    if header.get("alg") != ALGORITHM:
        raise MalformedToken(f"alg must be {ALGORITHM}")
    kid = header.get("kid")
    jwk = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if jwk is None:
        raise UnknownKid(f"no key for kid {kid!r}")
    try:
        claims = jwt.decode(
            token,
            RSAAlgorithm.from_jwk(jwk),
            algorithms=[ALGORITHM],
            # Tokens carry no audience: the auth service issues for one consumer only.
            options={"verify_aud": False, "require": REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredToken(str(exc)) from exc
    except jwt.InvalidSignatureError as exc:
        raise BadSignature(str(exc)) from exc
    except jwt.PyJWTError as exc:
        raise MalformedToken(str(exc)) from exc
    version = claims.get("version")
    # type() rather than isinstance(): True is an int, and must not pass as version 1.
    if type(version) is not int or version not in ACCEPTED_VERSIONS:
        raise UnsupportedVersion(f"claims version {version!r} not accepted")
    return Claims(sub=claims["sub"], role=claims["role"], version=version, exp=claims["exp"])
