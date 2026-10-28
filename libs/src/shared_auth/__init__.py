from importlib.metadata import version

from .errors import (
    BadSignature,
    ExpiredToken,
    MalformedToken,
    TokenError,
    UnknownKid,
    UnsupportedVersion,
)
from .ids import deterministic_uuid
from .roles import Role
from .tokens import ACCEPTED_VERSIONS, ISSUED_VERSION, Claims, issue, public_jwk, verify

__version__ = version("shared-auth")

__all__ = [
    "ACCEPTED_VERSIONS",
    "ISSUED_VERSION",
    "BadSignature",
    "Claims",
    "ExpiredToken",
    "MalformedToken",
    "Role",
    "TokenError",
    "UnknownKid",
    "UnsupportedVersion",
    "deterministic_uuid",
    "issue",
    "public_jwk",
    "verify",
]
