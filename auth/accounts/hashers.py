"""Verify WordPress password hashes copied verbatim from wp_users (R10, R28).

Django picks a hasher by the text before the first "$". WP hashes start with "$"
($P$, $H$, $wp$2y$), so that text is empty and Django cannot route them itself;
User.check_password sends them here and rehashes with the default hasher on success.
"""

import base64
import hashlib
import hmac

import bcrypt
from django.contrib.auth.hashers import BasePasswordHasher
from django.utils.crypto import constant_time_compare

WP_HASH_PREFIXES = ("$P$", "$H$", "$wp$2y$")
_ITOA64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def _encode64(data: bytes) -> str:
    """phpass's base64 variant: little-endian 6-bit groups over _ITOA64."""
    out = []
    for i in range(0, len(data), 3):
        chunk = data[i : i + 3]
        value = int.from_bytes(chunk, "little")
        out.extend(_ITOA64[(value >> shift) & 0x3F] for shift in range(0, 6 * (len(chunk) + 1), 6))
    return "".join(out)


def _phpass(password: bytes, setting: str) -> str | None:
    """Portable phpass (MD5, iterated), as WordPress used before 6.8."""
    count_log2 = _ITOA64.find(setting[3:4])
    salt = setting[4:12]
    if not 7 <= count_log2 <= 30 or len(salt) != 8:
        return None
    digest = hashlib.md5(salt.encode() + password).digest()
    for _ in range(1 << count_log2):
        digest = hashlib.md5(digest + password).digest()
    return setting[:12] + _encode64(digest)


def _wp_bcrypt(password: bytes, encoded: str) -> bool:
    """WP 6.8+: "$wp" + bcrypt of base64(HMAC-SHA384(password, "wp-sha384"))."""
    prehash = base64.b64encode(hmac.digest(b"wp-sha384", password, "sha384"))
    try:
        return bcrypt.checkpw(prehash, encoded[3:].encode())
    except ValueError:
        return False


class WordPressPasswordHasher(BasePasswordHasher):
    algorithm = "wordpress"

    def verify(self, password, encoded):
        raw = password.encode()
        if encoded.startswith("$wp$2y$"):
            return _wp_bcrypt(raw, encoded)
        if encoded.startswith(("$P$", "$H$")):
            computed = _phpass(raw, encoded)
            return computed is not None and constant_time_compare(computed, encoded)
        return False

    def encode(self, password, salt):
        raise NotImplementedError("WordPress hashes are verified on import, never created.")

    def decode(self, encoded):
        return {"algorithm": "wordpress", "hash": encoded, "salt": None}

    def safe_summary(self, encoded):
        return {"algorithm": "wordpress", "hash": f"{encoded[:7]}…"}

    def harden_runtime(self, password, encoded):
        pass
