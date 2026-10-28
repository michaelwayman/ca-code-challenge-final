"""The one RSA signing key (R14): AUTH_KEYS_DIR/signing.pem, created on first start.

The kid is a SHA-256 thumbprint of the public key, so replacing the file changes the kid.
A verifier that sees an unknown kid refetches the JWKS (R9) and picks the new key up.
There is no key ring or rotation tooling; key rotation is listed as production work.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from jwt.algorithms import RSAAlgorithm


@dataclass(frozen=True)
class SigningKey:
    kid: str
    private_key: rsa.RSAPrivateKey


def _path() -> Path:
    return Path(settings.AUTH_KEYS_DIR) / "signing.pem"


def _kid(private_key: rsa.RSAPrivateKey) -> str:
    der = private_key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(der).hexdigest()[:16]


def ensure_key() -> bool:
    """Generate signing.pem if it does not exist. Returns True when a key was created."""
    path = _path()
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)
    return True


def signing_key() -> SigningKey:
    path = _path()
    if not path.exists():
        raise RuntimeError(f"no signing key at {path}; run manage.py ensure_signing_key")
    private_key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    return SigningKey(kid=_kid(private_key), private_key=private_key)


def jwks() -> dict:
    key = signing_key()
    jwk = RSAAlgorithm.to_jwk(key.private_key.public_key(), as_dict=True)
    return {"keys": [{**jwk, "kid": key.kid, "alg": "RS256", "use": "sig"}]}
