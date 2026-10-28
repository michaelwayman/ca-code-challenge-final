"""Signing key ring: one PEM file per key in AUTH_KEYS_DIR, named <kid>.pem.

Kids are UTC timestamps, so the lexically last file is the newest and signs new tokens.
Every key in the directory is published in the JWKS, which keeps tokens signed by an older
key verifiable until they expire. Retire a key by deleting its file once its last
token is older than ACCESS_TOKEN_TTL.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from shared_auth import public_jwk


@dataclass(frozen=True)
class SigningKey:
    kid: str
    private_key: rsa.RSAPrivateKey


def _keys_dir() -> Path:
    return Path(settings.AUTH_KEYS_DIR)


def load_keys() -> list[SigningKey]:
    """All keys, oldest first."""
    keys = []
    for path in sorted(_keys_dir().glob("*.pem")):
        private_key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        keys.append(SigningKey(kid=path.stem, private_key=private_key))
    return keys


def active_key() -> SigningKey:
    keys = load_keys()
    if not keys:
        raise RuntimeError(f"no signing key in {_keys_dir()}; run manage.py add_signing_key")
    return keys[-1]


def add_key() -> str:
    """Generate a new RSA key; it becomes the active signer. Returns its kid."""
    directory = _keys_dir()
    directory.mkdir(parents=True, exist_ok=True)
    kid = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    path = directory / f"{kid}.pem"
    path.write_bytes(pem)
    path.chmod(0o600)
    return kid


def jwks() -> dict:
    return {"keys": [public_jwk(key.private_key.public_key(), key.kid) for key in load_keys()]}
