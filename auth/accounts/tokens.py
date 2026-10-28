import secrets
from datetime import UTC, datetime

from django.conf import settings
from shared_auth import issue

from .keys import active_key
from .models import RefreshToken, User


def issue_access_token(user: User) -> str:
    key = active_key()
    return issue(
        sub=str(user.pk),
        role=user.role,
        private_key=key.private_key,
        kid=key.kid,
        ttl=settings.ACCESS_TOKEN_TTL,
    )


def issue_refresh_token(user: User) -> str:
    raw = secrets.token_urlsafe(32)
    RefreshToken.objects.create(
        user=user,
        token_hash=RefreshToken.hash(raw),
        expires_at=datetime.now(UTC) + settings.REFRESH_TOKEN_TTL,
    )
    return raw


def find_live_refresh_token(raw: str) -> RefreshToken | None:
    """The unrevoked, unexpired token for an active user, else None."""
    return (
        RefreshToken.objects.live()
        .select_related("user")
        .filter(token_hash=RefreshToken.hash(raw))
        .first()
    )


def revoke(raw: str) -> None:
    RefreshToken.objects.filter(token_hash=RefreshToken.hash(raw)).revoke()


def access_token_response(user: User) -> dict:
    # Role is read from the user row at issue time, so admin changes land on next refresh.
    return {
        "access_token": issue_access_token(user),
        "token_type": "Bearer",
        "expires_in": int(settings.ACCESS_TOKEN_TTL.total_seconds()),
    }


def token_pair(user: User) -> dict:
    return {**access_token_response(user), "refresh_token": issue_refresh_token(user)}
