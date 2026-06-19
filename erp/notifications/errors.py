"""Notifications error catalog (NOT-NNN)."""
from __future__ import annotations

from erp.core.errors import AppError


class UnknownNotificationError(AppError):
    code = "NOT-001"
    status_code = 404
    message = "Notification not found"
