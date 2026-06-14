"""Development settings."""
from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS

DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]

# Friendlier in dev; tighten in prod.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]

# Make jobs run inline unless a worker is explicitly wanted.
# (Override with CELERY_TASK_ALWAYS_EAGER=false once a worker is running.)
