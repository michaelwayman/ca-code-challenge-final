import jwt
from jwt.algorithms import RSAAlgorithm

from .errors import BadSignature, ExpiredToken, MalformedToken, UnknownKid, UnsupportedVersion

CLAIMS_VERSION = 2
SUPPORTED_VERSIONS = frozenset({CLAIMS_VERSION - 1, CLAIMS_VERSION})  # N and N-1


def verify(token: str, jwks: dict) -> dict:
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
        claims = jwt.decode(
            token,
            RSAAlgorithm.from_jwk(jwk),
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredToken(str(exc)) from exc
    except jwt.InvalidSignatureError as exc:
        raise BadSignature(str(exc)) from exc
    except jwt.PyJWTError as exc:
        raise MalformedToken(str(exc)) from exc
    version = claims.get("version")
    if type(version) is not int or version not in SUPPORTED_VERSIONS:
        raise UnsupportedVersion(f"claims version {version!r} not supported")
    return claims
