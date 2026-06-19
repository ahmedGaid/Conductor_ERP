"""Django discovers models here; definitions live in the domain layer (strict module layout)."""
from __future__ import annotations

from .domain.models import Notification, NotificationChannel, NotificationStatus  # noqa: F401

__all__ = ["Notification", "NotificationChannel", "NotificationStatus"]
