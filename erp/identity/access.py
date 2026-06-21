"""Access service layer — the single place that answers "may this user do X?".

Reads the granular RBAC tables (``RolePermission`` / ``ApprovalLimit``) for a user's roles and
collapses them into simple answers: does the user hold a permission, at what data scope, which
modules can they reach, and may they approve a document of a given amount.

Superusers and the **System Admin** role bypass every check (matching the existing ``HasAnyRole``
semantics), so this is a strict superset of the role-name model it sits beside.
"""
from __future__ import annotations

from .rbac import DataScope, broadest, module_of
from .roles import SYSTEM_ADMIN


def is_superadmin(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return SYSTEM_ADMIN in set(user.roles)


def user_permissions(user) -> dict[str, str]:
    """Map of permission code -> effective (broadest) scope across all of the user's roles."""
    from .models import RolePermission

    result: dict[str, str] = {}
    rows = RolePermission.objects.filter(role__user=user).values_list("code", "scope")
    for code, scope in rows:
        result[code] = broadest(result[code], scope) if code in result else scope
    return result


def has_permission(user, code: str) -> bool:
    """True if the user holds ``code`` (or is a superadmin, who holds everything)."""
    if is_superadmin(user):
        return True
    if not user or not user.is_authenticated:
        return False
    from .models import RolePermission

    return RolePermission.objects.filter(role__user=user, code=code).exists()


def scope_for(user, code: str) -> str:
    """The broadest data scope at which the user holds ``code`` (ALL for a superadmin)."""
    if is_superadmin(user):
        return DataScope.ALL
    return user_permissions(user).get(code, DataScope.OWN)


def accessible_modules(user) -> list[str]:
    """Modules the user can reach — any module they hold at least one permission in.

    The frontend uses this to hide modules a user has no access to (Increment 4 wires it to the
    sidebar/routes). A superadmin reaches every module.
    """
    from .rbac import MODULE_NAMES

    if is_superadmin(user):
        return list(MODULE_NAMES)
    modules = {module_of(code) for code in user_permissions(user)}
    return [m for m in MODULE_NAMES if m in modules]


def approval_limit(user, document_type: str) -> int | None:
    """The user's approval ceiling (minor units) for a document type.

    Returns ``None`` for "unlimited" — which a superadmin always gets, and which also results from a
    role whose limit row is explicitly null. The broadest (highest / unlimited) limit across the
    user's roles wins. Returns ``0`` when the user has no limit row at all (cannot approve).
    """
    if is_superadmin(user):
        return None
    from .models import ApprovalLimit

    rows = list(
        ApprovalLimit.objects.filter(role__user=user, document_type=document_type).values_list(
            "limit_minor", flat=True
        )
    )
    if not rows:
        return 0
    if any(r is None for r in rows):
        return None  # an unlimited grant wins
    return max(rows)


def can_approve(user, document_type: str, amount_minor: int) -> bool:
    """True if the user may approve ``amount_minor`` of ``document_type``.

    Deny-by-default: a user with no configured limit cannot approve. Use this for the explicit
    document-approval step (orders/quotations/PRs), where the elevated role is granted a limit.
    """
    limit = approval_limit(user, document_type)
    if limit is None:
        return True  # unlimited
    return amount_minor <= limit


def within_limit(user, document_type: str, amount_minor: int) -> bool:
    """True if ``amount_minor`` of ``document_type`` is within the user's configured ceiling.

    **Opt-in** (the admin decides): if no approval limit is configured for any of the user's roles on
    this document type, the user is unconstrained — the admin simply hasn't capped it in the role
    editor. When a ceiling *is* configured it is enforced (a null ceiling = unlimited). Superuser /
    System Admin are always within limit. Use this for operational transaction caps
    (journal / invoice / payment) that an admin tunes per role; contrast ``can_approve`` above, which
    denies by default for the explicit approval step.
    """
    if is_superadmin(user):
        return True
    from .models import ApprovalLimit

    rows = list(
        ApprovalLimit.objects.filter(role__user=user, document_type=document_type).values_list(
            "limit_minor", flat=True
        )
    )
    if not rows:
        return True  # admin hasn't configured a cap for this role/document → unconstrained
    if any(r is None for r in rows):
        return True  # an unlimited grant wins
    return amount_minor <= max(rows)
