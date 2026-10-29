from rest_framework import authentication, exceptions, permissions

from .errors import TokenError
from .tokens import Claims, Role, verify


class TokenUser:
    """Request user built purely from verified claims; never touches a database."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, claims: Claims):
        self.claims = claims
        self.id = self.pk = claims.user_id
        self.role = claims.role


class JWTAuthentication(authentication.BaseAuthentication):
    """Verify a Bearer token. Subclass and set `get_jwks` (callable returning a JWKS dict)."""

    keyword = "Bearer"

    def get_jwks(self) -> dict:
        raise NotImplementedError("subclass JWTAuthentication and provide get_jwks()")

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Invalid Authorization header.")
        try:
            claims = verify(header[1].decode(), self.get_jwks())
        except (TokenError, UnicodeDecodeError) as exc:
            raise exceptions.AuthenticationFailed(str(exc)) from exc
        return TokenUser(claims), claims

    def authenticate_header(self, request):
        return self.keyword  # makes DRF answer 401 rather than 403


class IsEditor(permissions.BasePermission):
    """Editor role only. Unauthenticated requests are a 401 when JWTAuthentication is first."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            getattr(user, "is_authenticated", False) and getattr(user, "role", None) == Role.EDITOR
        )
