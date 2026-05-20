from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)

SECRET_KEY = "django-insecure-dev-key-change-in-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "migrator",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "migrator" / "templates"],
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


WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
    "oracle_source": {
        "ENGINE": "django.db.backends.oracle",  # keep for Django ORM (optional)
        "NAME": os.environ.get("ORACLE_DSN", "192.0.0.0:1521/AIT"),
        "USER": os.environ.get("ORACLE_USER", "AG"),
        "PASSWORD": os.environ.get("ORACLE_PASS", "A"),
        "HOST": "",
        "PORT": "",
        "OPTIONS": {
            "use_oracledb": True,  # tells Django to use oracledb driver
        },
    },
    "postgres_target": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PG_DB", "fast_erp"),
        "USER": os.environ.get("PG_USER", "postgres"),
        "PASSWORD": os.environ.get("PG_PASS", "AIT4allied"),
        "HOST": os.environ.get("PG_HOST", "localhost"),
        "PORT": os.environ.get("PG_PORT", "5432"),
        "OPTIONS": {
            "options": f"-c search_path={os.environ.get('PG_SCHEMA', 'ag')},public"
        },
    },
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
