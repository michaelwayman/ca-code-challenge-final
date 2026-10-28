"""Verify WordPress password hashes copied verbatim from wp_users.

Why this file exists
    The import keeps each user's WordPress hash untouched, so people keep their password
    without a reset. Django cannot check those hashes itself, so this module re-implements
    the two schemes WordPress has used:

    * "$P$..." / "$H$..."  phpass, WordPress before 6.8 (iterated MD5)
    * "$wp$2y$..."         WordPress 6.8+ (bcrypt over a SHA-384 prehash)

How a login reaches it
    Django normally picks a hasher by the text before the first "$" (e.g. "pbkdf2_sha256$...").
    WP hashes start with "$", so that text is empty and Django cannot route them.
    Instead, User.check_password (accounts/models.py) notices a WP prefix, calls
    WordPressPasswordHasher.verify, and on success calls set_password, which rehashes the
    password with the default hasher (PBKDF2). Each WP hash is therefore upgraded to Django's
    own format the first time its owner logs in; after that this code is no longer used for
    that user.

What it deliberately does not do
    It never creates WP hashes (encode raises) and never needs hardening, because a WP hash
    is replaced as soon as it verifies once.
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
    """phpass's own base64 (not RFC 4648), used to print the final MD5 digest.

    Takes the bytes three at a time, reads them as one little-endian number and emits its
    6-bit groups, lowest first, using the alphabet in _ITOA64 ("./0-9A-Za-z"). A leftover
    chunk of 1 or 2 bytes yields 2 or 3 characters. The 16-byte MD5 digest gives 22 characters.
    Standard base64 differs in both byte order and alphabet, so it cannot be used here.
    """
    out = []
    for i in range(0, len(data), 3):
        chunk = data[i : i + 3]
        value = int.from_bytes(chunk, "little")
        out.extend(_ITOA64[(value >> shift) & 0x3F] for shift in range(0, 6 * (len(chunk) + 1), 6))
    return "".join(out)


def _phpass(password: bytes, setting: str) -> str | None:
    """Recompute a phpass hash from `setting` (the stored hash, or just its first 12 chars).

    A stored hash looks like "$P$B" + 8 salt chars + 22 hash chars:

        $P$   phpass marker ("$H$" is the same scheme, used by older phpBB-style tools)
        B     cost: the character's index in _ITOA64 is log2 of the iteration count
              (WordPress uses "B", index 13, so 2**13 = 8192 rounds)
        salt  the next 8 characters, used as-is
        hash  _encode64 of the final digest

    Algorithm: digest = MD5(salt + password), then `2**cost` times digest = MD5(digest + password).
    The result is the first 12 characters of the stored value plus _encode64(digest). Returns
    None if the cost or salt is malformed (so verify fails instead of raising).
    """
    count_log2 = _ITOA64.find(setting[3:4])
    salt = setting[4:12]
    if not 7 <= count_log2 <= 30 or len(salt) != 8:
        return None
    digest = hashlib.md5(salt.encode() + password).digest()
    for _ in range(1 << count_log2):
        digest = hashlib.md5(digest + password).digest()
    return setting[:12] + _encode64(digest)


def _wp_bcrypt(password: bytes, encoded: str) -> bool:
    """WordPress 6.8+: "$wp" followed by an ordinary bcrypt hash ("$wp$2y$10$...").

    WordPress does not feed the password to bcrypt directly (bcrypt truncates at 72 bytes and
    stops at NUL bytes). It first prehashes: base64(HMAC-SHA384(key="wp-sha384", msg=password)),
    which is always 64 printable characters, and bcrypts that. We repeat the prehash, drop the
    leading "$wp" so what remains ("$2y$10$...") is a standard bcrypt hash, and let bcrypt
    compare. A malformed hash makes bcrypt raise ValueError, which we report as a failed check.
    """
    prehash = base64.b64encode(hmac.digest(b"wp-sha384", password, "sha384"))
    try:
        return bcrypt.checkpw(prehash, encoded[3:].encode())
    except ValueError:
        return False


class WordPressPasswordHasher(BasePasswordHasher):
    """Read-only Django hasher for WP hashes; registered in PASSWORD_HASHERS (settings.py).

    Only `verify` does real work. The other methods exist because Django's hasher interface
    requires them (the admin shows `safe_summary` for a user's password field).
    """

    algorithm = "wordpress"

    def verify(self, password, encoded):
        """True if `password` matches the WP hash `encoded`; False for any other format."""
        raw = password.encode()
        if encoded.startswith("$wp$2y$"):
            return _wp_bcrypt(raw, encoded)
        if encoded.startswith(("$P$", "$H$")):
            computed = _phpass(raw, encoded)
            # Compare in constant time so response timing does not leak how many characters matched.
            return computed is not None and constant_time_compare(computed, encoded)
        return False

    def encode(self, password, salt):
        raise NotImplementedError("WordPress hashes are verified on import, never created.")

    def decode(self, encoded):
        return {"algorithm": "wordpress", "hash": encoded, "salt": None}

    def safe_summary(self, encoded):
        return {"algorithm": "wordpress", "hash": f"{encoded[:7]}…"}

    def harden_runtime(self, password, encoded):
        # Django calls this to equalise login timing for stale hashes; nothing to harden here.
        pass
