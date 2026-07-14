"""Shared role gate for import adapters — mirrors ``HasAnyRole`` (the DRF permission class every
module's own write endpoints use). Contract write-paths like ``sales.create_customer`` don't check
permissions themselves (that lives in the API view layer); the import engine can run outside HTTP
(background jobs), so each adapter's ``write`` enforces the same gate here before calling the
module. Pattern copied from ``erp.assistant.services.actions._can`` — not a new permission system.
"""
from __future__ import annotations

from erp.identity.roles import SYSTEM_ADMIN


def require_role(actor, *roles: str) -> None:
    """Raise ``PermissionError`` unless ``actor`` is a superuser, System Admin, or holds one of
    ``roles``. Bare ``PermissionError`` (no message) — matches the existing convention in
    ``erp.assistant.services.actions``."""
    if not getattr(actor, "is_authenticated", False):
        raise PermissionError
    if getattr(actor, "is_superuser", False):
        return
    held = set(actor.roles)
    if SYSTEM_ADMIN in held or held.intersection(roles):
        return
    raise PermissionError
