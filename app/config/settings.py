"""Main app settings. Dev-grade by design (O8). Holds credentials for its own DB only (C2)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-only-app-secret")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "rest_framework",
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
        "HOST": os.environ.get("APP_DB_HOST", "app-db"),
        "PORT": os.environ.get("APP_DB_PORT", "5432"),
        "NAME": os.environ.get("APP_DB_NAME", "app"),
        "USER": os.environ.get("APP_DB_USER", "app"),
        "PASSWORD": os.environ.get("APP_DB_PASSWORD", "app"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
