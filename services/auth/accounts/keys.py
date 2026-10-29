"""Signing key ring: one PEM file per key in AUTH_KEYS_DIR, named <kid>.pem.

Kids are UTC timestamps, so the lexically last file is the newest and signs new tokens.
Every key in the directory is published in the JWKS, which keeps tokens signed by an older
key verifiable until they expire (R14). Retire a key by deleting its file once its last
token is older than ACCESS_TOKEN_TTL.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from jwt.algorithms import RSAAlgorithm


@dataclass(frozen=True)
class SigningKey:
    kid: str
    private_key: rsa.RSAPrivateKey


def _keys_dir() -> Path:
    return Path(settings.AUTH_KEYS_DIR)


_loaded: tuple[tuple, list[SigningKey]] | None = None


def load_keys() -> list[SigningKey]:
    """All keys, oldest first. Parsed keys are reused until a key file is added, removed or
    changed, so rotation takes effect on the next call without re-reading the disk each time."""
    global _loaded
    paths = sorted(_keys_dir().glob("*.pem"))
    stamp = (str(_keys_dir()), *((p.name, p.stat().st_mtime_ns) for p in paths))
    if _loaded is None or _loaded[0] != stamp:
        keys = [
            SigningKey(
                kid=p.stem,
                private_key=serialization.load_pem_private_key(p.read_bytes(), password=None),
            )
            for p in paths
        ]
        _loaded = (stamp, keys)
    return list(_loaded[1])


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
    keys = []
    for key in load_keys():
        jwk = RSAAlgorithm.to_jwk(key.private_key.public_key(), as_dict=True)
        keys.append({**jwk, "kid": key.kid, "alg": "RS256", "use": "sig"})
    return {"keys": keys}
