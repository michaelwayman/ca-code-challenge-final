import hashlib
import uuid

from cauth import Role
from django.contrib.auth.hashers import get_hasher
from django.contrib.auth.models import AbstractUser
from django.db import models

from .hashers import WP_HASH_PREFIXES


class User(AbstractUser):
    # UUID pk so imported WP users get wp_user_uuid(id) (R10, A3).
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=16, choices=[(r.value, r.value) for r in Role], default=Role.READER
    )

    def check_password(self, raw_password):
        # Imported WP hashes are stored verbatim (R10); verify, then rehash (R28).
        if not self.password.startswith(WP_HASH_PREFIXES):
            return super().check_password(raw_password)
        if not get_hasher("wordpress").verify(raw_password, self.password):
            return False
        self.set_password(raw_password)
        self.save(update_fields=["password"])
        return True


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
