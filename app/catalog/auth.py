"""Token authentication against the auth service. The main app never calls the auth service
per request: it verifies tokens locally with public keys from the JWKS, cached in process.
While the auth service is down the last good key set keeps working; with a cold cache and
the auth service down there is nothing to verify against, so writes fail closed with a 503."""

import json
import logging
import threading
import time
import urllib.request

from django.conf import settings
from rest_framework import exceptions
from shared_auth.drf import JWTAuthentication

logger = logging.getLogger(__name__)


class KeysUnavailable(exceptions.APIException):
    status_code = 503
    default_detail = "Signing keys unavailable; the auth service could not be reached."
    default_code = "keys_unavailable"


def is_jwks(data):
    """A malformed key set is treated like a failed fetch, so it can never reach the
    verifier and turn every write into a 500."""
    keys = data.get("keys") if isinstance(data, dict) else None
    return isinstance(keys, list) and all(isinstance(key, dict) for key in keys)


class JWKSCache:
    """The auth service's key set, refetched after `max_age` seconds. A failed fetch keeps
    the previous set and is not retried for `retry_after` seconds, so an outage costs one
    timeout per window rather than one per request. Refetches for an unknown kid share that
    window, so a flood of forged kids cannot hammer the auth service."""

    def __init__(self, url, max_age, retry_after, timeout):
        self.url = url
        self.max_age = max_age
        self.retry_after = retry_after
        self.timeout = timeout
        self._lock = threading.Lock()
        self._jwks = None
        self._expires_at = 0.0
        self._next_attempt = 0.0

    def get(self):
        with self._lock:
            now = time.monotonic()
            if now >= self._expires_at and now >= self._next_attempt:
                self._fetch(now)
            if self._jwks is None:
                raise KeysUnavailable()
            return self._jwks

    def refresh(self):
        """Refetch now (an unknown kid may mean the auth service rotated keys).
        Returns True only when a new key set was fetched."""
        with self._lock:
            now = time.monotonic()
            if now < self._next_attempt:
                return False
            self._next_attempt = now + self.retry_after
            return self._fetch(now)

    def clear(self):
        with self._lock:
            self._jwks = None
            self._expires_at = self._next_attempt = 0.0

    def _fetch(self, now):
        try:
            with urllib.request.urlopen(self.url, timeout=self.timeout) as response:
                jwks = json.load(response)
            if not is_jwks(jwks):
                raise ValueError("response is not a JWKS")
        except (OSError, ValueError) as exc:
            stale = "keeping cached keys" if self._jwks else "no cached keys"
            logger.warning("JWKS fetch from %s failed (%s); %s", self.url, exc, stale)
            self._next_attempt = now + self.retry_after
            return False
        self._jwks = jwks
        self._expires_at = now + self.max_age
        return True


jwks_cache = JWKSCache(
    settings.AUTH_JWKS_URL,
    max_age=settings.JWKS_CACHE_SECONDS,
    retry_after=settings.JWKS_RETRY_SECONDS,
    timeout=settings.JWKS_TIMEOUT_SECONDS,
)


class AuthServiceJWT(JWTAuthentication):
    key_source = jwks_cache
