"""Django REST framework glue. Needs the `drf` extra: pip install 'shared-auth[drf]'."""

from typing import Protocol

from rest_framework import authentication, exceptions, permissions

from .errors import TokenError, UnknownKid
from .roles import Role
from .tokens import Claims, verify


class KeySource(Protocol):
    def get(self) -> dict:
        """The current JWKS."""

    def refresh(self) -> bool:
        """Refetch the JWKS now; True only if a new key set was loaded."""


class TokenUser:
    """Request user built purely from verified claims; never touches a database."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, claims: Claims):
        self.claims = claims
        self.id = claims.sub
        self.role = claims.role


class JWTAuthentication(authentication.BaseAuthentication):
    """Verify a Bearer token. Subclass and set `key_source`.

    A token signed by an unknown kid triggers one `key_source.refresh()` and a second try,
    since the auth service may have rotated in a new key.
    """

    keyword = "Bearer"
    key_source: KeySource

    def authenticate(self, request):
        token = self._bearer_token(request)
        if token is None:
            return None
        try:
            claims = self._verify(token)
        except TokenError as exc:
            raise exceptions.AuthenticationFailed(str(exc)) from exc
        return TokenUser(claims), claims

    def authenticate_header(self, request):
        return self.keyword  # makes DRF answer 401 rather than 403

    def _bearer_token(self, request) -> str | None:
        """The token, None for no or another scheme, AuthenticationFailed if malformed."""
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Invalid Authorization header.")
        try:
            return header[1].decode()
        except UnicodeDecodeError as exc:
            raise exceptions.AuthenticationFailed("Invalid Authorization header.") from exc

    def _verify(self, token: str) -> Claims:
        try:
            return verify(token, self.key_source.get())
        except UnknownKid:
            if not self.key_source.refresh():
                raise
            return verify(token, self.key_source.get())


class IsEditor(permissions.BasePermission):
    """Editor role only. Unauthenticated requests are a 401 when JWTAuthentication is first."""

    def has_permission(self, request, view):
        return isinstance(request.user, TokenUser) and request.user.role == Role.EDITOR
