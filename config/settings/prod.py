"""Production settings (customer-hosted, single-tenant, Windows Server capable)."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# In prod the secret must be provided; no insecure default.
SECRET_KEY = env("DJANGO_SECRET_KEY")

# --- Security hardening (OWASP / Django deployment checklist) ---
# Header / cookie hardening.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = env.bool("DJANGO_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("DJANGO_COOKIE_SECURE", default=True)

# HTTPS: redirect, HSTS, and trust the reverse proxy's forwarded-proto header (IIS/Nginx in front).
# All env-tunable so an HTTP-only internal install can relax them, but they default to secure.
SECURE_SSL_REDIRECT = env.bool("DJANGO_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF: trust the configured public origin(s) for unsafe requests (empty by default).
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# CORS: the SPA is served behind Django (same origin) in prod, so cross-origin is closed by default;
# add explicit origins via env only if the frontend is hosted separately.
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])
