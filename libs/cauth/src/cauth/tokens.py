"""Access-token claims and their verification: the contract between the auth service, which
issues tokens, and the main app, which verifies them. Both sides use `Claims`, so the shape
lives in one place (docs/contracts/auth/token-claims.schema.json describes it for humans)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

import jwt
from jwt.algorithms import RSAAlgorithm

from .errors import BadSignature, ExpiredToken, MalformedToken, UnknownKid, UnsupportedVersion

CLAIMS_VERSION = 2
SUPPORTED_VERSIONS = frozenset({CLAIMS_VERSION - 1, CLAIMS_VERSION})  # N and N-1

# PyJWT only checks a claim that is present, so these are demanded: a token without `exp` would
# never expire and one without `role` would reach the permission check.
REQUIRED_CLAIMS = ["exp", "iat", "sub", "role"]


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

    def to_payload(self) -> dict:
        return {
            "sub": self.user_id,
            "role": self.role.value,
            "iat": int(self.issued_at.timestamp()),
            "exp": int(self.expires_at.timestamp()),
            "version": self.version,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "Claims":
        """Claims from a decoded JWT payload, or a TokenError if it is not a valid one."""
        version = payload.get("version")
        if type(version) is not int or version not in SUPPORTED_VERSIONS:
            raise UnsupportedVersion(f"claims version {version!r} not supported")
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise MalformedToken("sub must be a string")
        try:
            role = Role(payload.get("role"))
        except ValueError as exc:
            raise MalformedToken(f"unknown role {payload.get('role')!r}") from exc
        times = []
        for name in ("iat", "exp"):
            if type(payload.get(name)) is not int:
                raise MalformedToken(f"{name} must be an integer")
            times.append(datetime.fromtimestamp(payload[name], UTC))
        return cls(user_id, role, *times, version=version)


def verify(token: str, jwks: dict) -> Claims:
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
            RSAAlgorithm.from_jwk(jwk),
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
