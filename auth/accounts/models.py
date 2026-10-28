import hashlib
import uuid

from django.contrib.auth.hashers import get_hasher
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from shared_auth import Role

from .hashers import WP_HASH_PREFIXES


class User(AbstractUser):
    # UUID pk so imported WP users get deterministic_uuid('wp_user', id), the same id the
    # main app gives their reviewer profile.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=16, choices=[(r, r) for r in Role], default=Role.READER)

    def check_password(self, raw_password):
        # Imported WP hashes are stored verbatim; verify, then rehash to Django's default.
        if not self.password.startswith(WP_HASH_PREFIXES):
            return super().check_password(raw_password)
        if not get_hasher("wordpress").verify(raw_password, self.password):
            return False
        self.set_password(raw_password)
        self.save(update_fields=["password"])
        return True


class RefreshTokenQuerySet(models.QuerySet):
    def live(self):
        """Unrevoked, unexpired tokens of active users."""
        return self.filter(
            revoked_at__isnull=True, expires_at__gt=timezone.now(), user__is_active=True
        )

    def revoke(self) -> int:
        """Revoke the unrevoked tokens in this queryset; returns how many."""
        return self.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())


class RefreshToken(models.Model):
    """Opaque refresh token; only its SHA-256 is stored, the raw value is shown once."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    objects = RefreshTokenQuerySet.as_manager()

    @staticmethod
    def hash(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()
