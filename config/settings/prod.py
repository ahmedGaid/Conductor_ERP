"""Production settings (customer-hosted, single-tenant, Windows Server capable)."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Security hardening (OWASP). HTTPS termination is environment-specific; enable when present.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env("DJANGO_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env("DJANGO_COOKIE_SECURE", default=True)

# In prod the secret must be provided; no insecure default.
SECRET_KEY = env("DJANGO_SECRET_KEY")
