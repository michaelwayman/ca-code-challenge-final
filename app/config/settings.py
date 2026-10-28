"""Main app settings. Dev-grade by design (O8). Holds credentials for its own DB only (C2)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-only-app-secret")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "catalog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]

# Compiled CSS/JS from frontend/dist (mounted at /srv/frontend); runserver serves it (O8).
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    p for p in [Path("/srv/frontend/dist"), BASE_DIR.parent / "frontend" / "dist"] if p.exists()
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("APP_DB_HOST", "app-db"),
        "PORT": os.environ.get("APP_DB_PORT", "5432"),
        "NAME": os.environ.get("APP_DB_NAME", "app"),
        "USER": os.environ.get("APP_DB_USER", "app"),
        "PASSWORD": os.environ.get("APP_DB_PASSWORD", "app"),
    }
}

# Read-only source for import_wp (R2): the WP MariaDB.
WP_DB = {
    "host": os.environ.get("WP_DB_HOST", "db"),
    "port": int(os.environ.get("WP_DB_PORT", "3306")),
    "database": os.environ.get("WP_DB_NAME", "wp"),
    "user": os.environ.get("WP_DB_USER", "wp"),
    "password": os.environ.get("WP_DB_PASSWORD", "wp"),
}
WP_TABLE_PREFIX = os.environ.get("WP_TABLE_PREFIX", "wp_")

# Public keys for token verification (R8, R9); see config/auth.py.
AUTH_JWKS_URL = os.environ.get("AUTH_JWKS_URL", "http://auth:8001/.well-known/jwks.json")
JWKS_CACHE_SECONDS = 300  # matches the auth service's Cache-Control max-age
JWKS_RETRY_SECONDS = 30  # wait after a failed fetch or a refetch for an unknown kid
JWKS_TIMEOUT_SECONDS = 2

# No django.contrib.auth here (C2): anonymous requests carry user None, JSON only.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "UNAUTHENTICATED_USER": None,
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
