"""Development settings."""
from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, REST_FRAMEWORK

DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]

# Friendlier in dev; tighten in prod.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]

# Disable DRF rate limiting in dev/test so the gate suite (which fires many requests in quick
# succession) is never throttled. Production keeps the base rates. The throttle *behaviour* is
# proven by a dedicated test that re-enables a tiny rate via override_settings (see gate12).
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"anon": None, "user": None}}

# Make jobs run inline unless a worker is explicitly wanted.
# (Override with CELERY_TASK_ALWAYS_EAGER=false once a worker is running.)
