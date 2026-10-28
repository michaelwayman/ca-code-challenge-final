"""Auth service settings. Dev-grade by design: DEBUG on, runserver, env-provided secrets."""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "dev-only-auth-secret")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    # Admin is the operator tool for roles and token revocation.
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

STATIC_URL = "static/"  # served by runserver with DEBUG on

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

# Django's default first (new and rehashed passwords), WP last for imported hashes.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "accounts.hashers.WordPressPasswordHasher",
]

# Read-only source for import_wp_users: MariaDB from the WP compose stack.
WP_DB = {
    "host": os.environ.get("WP_DB_HOST", "db"),
    "port": int(os.environ.get("WP_DB_PORT", "3306")),
    "database": os.environ.get("WP_DB_NAME", "wp"),
    "user": os.environ.get("WP_DB_USER", "wp"),
    "password": os.environ.get("WP_DB_PASSWORD", "wp"),
}
WP_TABLE_PREFIX = os.environ.get("WP_TABLE_PREFIX", "wp_")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"

# Token issuing: 10 min RS256 access token, public keys via JWKS.
AUTH_KEYS_DIR = Path(os.environ.get("AUTH_KEYS_DIR", BASE_DIR / "keys"))
ACCESS_TOKEN_TTL = timedelta(minutes=10)
REFRESH_TOKEN_TTL = timedelta(days=7)  # bounded, so a leaked refresh token stops working
JWKS_MAX_AGE = 300  # seconds consumers may cache the key set
