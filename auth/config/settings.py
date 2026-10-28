"""Auth service settings. Dev-grade by design (O8): DEBUG on, runserver, env-provided secrets."""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "dev-only-auth-secret")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("AUTH_DB_HOST", "auth-db"),
        "PORT": os.environ.get("AUTH_DB_PORT", "5432"),
        "NAME": os.environ.get("AUTH_DB_NAME", "auth"),
        "USER": os.environ.get("AUTH_DB_USER", "auth"),
        "PASSWORD": os.environ.get("AUTH_DB_PASSWORD", "auth"),
    }
}

AUTH_USER_MODEL = "accounts.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"

# Token issuing (Q6: 10 min RS256 access token, public keys via JWKS).
AUTH_KEYS_DIR = Path(os.environ.get("AUTH_KEYS_DIR", BASE_DIR / "keys"))
ACCESS_TOKEN_TTL = timedelta(minutes=10)
REFRESH_TOKEN_TTL = timedelta(days=7)  # A5: bounded lifetime
JWKS_MAX_AGE = 300  # seconds consumers may cache the key set
