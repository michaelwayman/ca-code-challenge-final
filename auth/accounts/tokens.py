import secrets
from datetime import UTC, datetime

import jwt
from cauth import CLAIMS_VERSION
from django.conf import settings

from .keys import active_key
from .models import RefreshToken, User


def issue_access_token(user: User) -> str:
    key = active_key()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.pk),
        "role": user.role,
        "iat": now,
        "exp": now + settings.ACCESS_TOKEN_TTL,
        "version": CLAIMS_VERSION,
    }
    return jwt.encode(claims, key.private_key, algorithm="RS256", headers={"kid": key.kid})


def issue_refresh_token(user: User) -> str:
    raw = secrets.token_urlsafe(32)
    RefreshToken.objects.create(
        user=user,
        token_hash=RefreshToken.hash(raw),
        expires_at=datetime.now(UTC) + settings.REFRESH_TOKEN_TTL,
    )
    return raw


def token_pair(user: User) -> dict:
    return {
        "access_token": issue_access_token(user),
        "token_type": "Bearer",
        "expires_in": int(settings.ACCESS_TOKEN_TTL.total_seconds()),
        "refresh_token": issue_refresh_token(user),
    }
