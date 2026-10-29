"""Access-token claims and their verification: the contract between the auth service, which
issues tokens, and the main app, which verifies them. Both sides use `Claims`, so the shape
lives in one place (docs/contracts/auth/token-claims.schema.json describes it for humans)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, NotRequired, TypedDict, cast

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm

from .errors import BadSignature, ExpiredToken, MalformedToken, UnknownKid, UnsupportedVersion

CLAIMS_VERSION = 2
SUPPORTED_VERSIONS = frozenset({CLAIMS_VERSION - 1, CLAIMS_VERSION})  # N and N-1

# PyJWT only checks a claim that is present, so these are demanded: a token without `exp` would
# never expire and one without `role` would reach the permission check.
REQUIRED_CLAIMS = ["exp", "iat", "sub", "role"]


class JWK(TypedDict):
    """One RSA public key as published in a JWKS (RFC 7517)."""

    kty: str
    kid: str
    n: str
    e: str
    alg: NotRequired[str]
    use: NotRequired[str]


class JWKS(TypedDict):
    keys: list[JWK]


class TokenPayload(TypedDict):
    """The JWT body `Claims.to_payload` writes; the field names are the wire contract."""

    sub: str
    role: str
    iat: int
    exp: int
    version: int


class Role(StrEnum):
    READER = "reader"
    EDITOR = "editor"


@dataclass(frozen=True)
class Claims:
    """What an access token says about its user. The JWT field names are in `to_payload`."""

    user_id: str
    role: Role
    issued_at: datetime
    expires_at: datetime
    version: int = CLAIMS_VERSION

    def to_payload(self) -> TokenPayload:
        return {
            "sub": self.user_id,
            "role": self.role.value,
            "iat": int(self.issued_at.timestamp()),
            "exp": int(self.expires_at.timestamp()),
            "version": self.version,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Claims":
        """Claims from a decoded JWT payload, or a TokenError if it is not a valid one."""
        version = payload.get("version")
        if type(version) is not int or version not in SUPPORTED_VERSIONS:
            raise UnsupportedVersion(f"claims version {version!r} not supported")
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise MalformedToken("sub must be a string")
        raw_role: Any = payload.get("role")
        try:
            role = Role(raw_role)
        except ValueError as exc:
            raise MalformedToken(f"unknown role {raw_role!r}") from exc
        for name in ("iat", "exp"):
            if type(payload.get(name)) is not int:
                raise MalformedToken(f"{name} must be an integer")
        issued_at = datetime.fromtimestamp(payload["iat"], UTC)
        expires_at = datetime.fromtimestamp(payload["exp"], UTC)
        return cls(user_id, role, issued_at, expires_at, version=version)


def verify(token: str, jwks: JWKS) -> Claims:
    """Return the claims of a valid RS256 token, or raise a TokenError subclass."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise MalformedToken(str(exc)) from exc
    if header.get("alg") != "RS256":
        raise MalformedToken("alg must be RS256")
    kid = header.get("kid")
    jwk = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if jwk is None:
        raise UnknownKid(f"no key for kid {kid!r}")
    try:
        payload = jwt.decode(
            token,
            # A JWKS holds public keys; from_jwk is typed as returning any key type.
            cast(RSAPublicKey, RSAAlgorithm.from_jwk(dict(jwk))),
            algorithms=["RS256"],
            options={"verify_aud": False, "require": REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredToken(str(exc)) from exc
    except jwt.InvalidSignatureError as exc:
        raise BadSignature(str(exc)) from exc
    except jwt.PyJWTError as exc:
        raise MalformedToken(str(exc)) from exc
    return Claims.from_payload(payload)
