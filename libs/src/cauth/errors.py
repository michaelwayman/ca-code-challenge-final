class TokenError(Exception):
    """Base class for all token verification failures."""


class MalformedToken(TokenError):
    pass


class UnknownKid(TokenError):
    pass


class BadSignature(TokenError):
    pass


class ExpiredToken(TokenError):
    pass


class UnsupportedVersion(TokenError):
    pass
