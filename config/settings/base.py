"""Base settings shared by all environments.

Customer-hosted, single-tenant. No cloud-only dependencies. Values come from the
environment (.env) so the same code runs on a dev box or a Windows Server install.
"""
from pathlib import Path

import environ

# config/settings/base.py -> repo root is three parents up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_IP_WHITELIST=(list, []),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
)

# Load .env if present (never required to exist in production where env is injected).
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    environ.Env.read_env(str(_env_file))

# --- Core ---
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
APP_VERSION = env("APP_VERSION", default="0.0.0")
IP_WHITELIST = env("DJANGO_IP_WHITELIST")  # empty list => allow all (dev)

# --- Applications ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
]
# ERP modules (modular monolith). Each is an isolated Django app under erp/.
LOCAL_APPS = [
    "erp.core",
    "erp.identity",
    "erp.audit",
    "erp.monitoring",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    # Correlation ID must wrap everything so every log/error/audit row carries it.
    "erp.core.middleware.CorrelationIdMiddleware",
    "erp.core.middleware.IpWhitelistMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database ---
DATABASES = {
    "default": {
        **env.db_url("DATABASE_URL", default="postgresql://erp:erp@localhost:5432/erp"),
        "ATOMIC_REQUESTS": False,  # explicit transactions in services (repository pattern)
    }
}
# Use psycopg v3.
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

# --- Custom user (set before first migration so the swap is clean) ---
AUTH_USER_MODEL = "identity.User"

# --- Password hashing (argon2 first) ---
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# --- i18n (Arabic-first; the UI defaults to ar/RTL) ---
LANGUAGE_CODE = "ar"
LANGUAGES = [("ar", "Arabic"), ("en", "English")]
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

# --- Static / media / storage ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGE_ROOT = Path(env("STORAGE_ROOT", default=str(BASE_DIR / "storage")))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "erp.core.exceptions.drf_exception_handler",
}

# --- JWT (access/refresh) ---
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

# --- Celery (Redis / Memurai) ---
_redis_url = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = _redis_url
CELERY_RESULT_BACKEND = _redis_url
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True  # recover jobs after a worker crash
CELERY_RESULT_EXTENDED = True

REDIS_URL = _redis_url

# --- CORS (frontend dev server) ---
CORS_ALLOWED_ORIGINS = [
    f"http://localhost:{env('WEB_PORT', default='5173')}",
    f"http://127.0.0.1:{env('WEB_PORT', default='5173')}",
]

# --- Logging: structured JSON only (no unstructured text logs) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "erp.core.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}
