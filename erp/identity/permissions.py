"""RBAC permission classes for DRF.

Every protected endpoint declares the roles it requires. Superusers and the System Admin role
bypass role checks. Use ``HasAnyRole.require("Accountant", "Branch Manager")`` in a view's
``permission_classes``.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from .roles import SYSTEM_ADMIN


class HasAnyRole(BasePermission):
    """Grant access if the user holds any of ``required_roles`` (or is admin)."""

    required_roles: tuple[str, ...] = ()

    @classmethod
    def require(cls, *roles: str) -> type["HasAnyRole"]:
        return type("HasAnyRole_" + "_".join(roles), (cls,), {"required_roles": tuple(roles)})

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        user_roles = set(user.roles)
        if SYSTEM_ADMIN in user_roles:
            return True
        return bool(user_roles.intersection(self.required_roles))
