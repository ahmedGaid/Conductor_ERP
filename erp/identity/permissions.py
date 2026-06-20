"""RBAC permission classes for DRF.

Every protected endpoint declares the roles it requires. Superusers and the System Admin role
bypass role checks. Use ``HasAnyRole.require("Accountant", "Branch Manager")`` in a view's
``permission_classes``.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from . import access
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


class HasModulePermission(BasePermission):
    """Grant access if the user holds the required granular permission code(s).

    This is the granular successor to ``HasAnyRole`` and a strict superset of it: superusers and the
    System Admin role bypass, exactly as before. Existing endpoints keep using ``HasAnyRole`` until
    they are migrated one at a time (a later increment); new endpoints can opt into this today via
    ``HasModulePermission.require("sales.order.view")``. When several codes are required, ALL must be
    held (use one code per view for the common case).
    """

    required_codes: tuple[str, ...] = ()

    @classmethod
    def require(cls, *codes: str) -> type["HasModulePermission"]:
        return type(
            "HasModulePermission_" + "_".join(c.replace(".", "_") for c in codes),
            (cls,),
            {"required_codes": tuple(codes)},
        )

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if access.is_superadmin(user):
            return True
        return all(access.has_permission(user, c) for c in self.required_codes)
