import secrets
from datetime import UTC, datetime

import jwt
from cauth import Claims, Role
from django.conf import settings

from .keys import active_key
from .models import RefreshToken, User


def issue_access_token(user: User) -> str:
    key = active_key()
    now = datetime.now(UTC).replace(microsecond=0)
    claims = Claims(
        user_id=str(user.pk),
        role=Role(user.role),
        issued_at=now,
        expires_at=now + settings.ACCESS_TOKEN_TTL,
    )
    return jwt.encode(
        claims.to_payload(), key.private_key, algorithm="RS256", headers={"kid": key.kid}
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
        RefreshToken.objects.select_related("user")
        .filter(
            token_hash=RefreshToken.hash(raw),
            revoked_at__isnull=True,
            expires_at__gt=datetime.now(UTC),
            user__is_active=True,
        )
        .first()
    )


def revoke(raw: str) -> None:
    RefreshToken.objects.filter(token_hash=RefreshToken.hash(raw), revoked_at__isnull=True).update(
        revoked_at=datetime.now(UTC)
    )


def access_token_response(user: User) -> dict:
    # Role is read from the user row at issue time, so admin changes land on next refresh (R12).
    return {
        "access_token": issue_access_token(user),
        "token_type": "Bearer",
        "expires_in": int(settings.ACCESS_TOKEN_TTL.total_seconds()),
    }


def token_pair(user: User) -> dict:
    return {**access_token_response(user), "refresh_token": issue_refresh_token(user)}
