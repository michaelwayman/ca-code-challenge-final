class TokenError(Exception):
    """Base class for all token verification failures."""


class MalformedToken(TokenError):
    """Not a JWT, the wrong algorithm, or a required claim is missing."""


class UnknownKid(TokenError):
    """Signed by a key the given JWKS does not contain (it may have been rotated in)."""


class BadSignature(TokenError):
    """The signature does not match the key named by its kid."""


class ExpiredToken(TokenError):
    """The exp claim is in the past."""


class UnsupportedVersion(TokenError):
    """The version claim is missing or not in ACCEPTED_VERSIONS."""
