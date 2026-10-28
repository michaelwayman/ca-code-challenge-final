import hashlib
import uuid

from cauth import READER, ROLES
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # UUID pk so imported WP users get deterministic_uuid('wp_user', id) (R10, A3).
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=16, choices=[(r, r) for r in ROLES], default=READER)


class RefreshToken(models.Model):
    """Opaque refresh token; only its SHA-256 is stored, the raw value is shown once."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def hash(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()
