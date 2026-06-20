"""Role administration service (Increment 4) — manage roles and their granular grants.

A role is a Django Group carrying ``RolePermission`` + ``ApprovalLimit`` rows (Increment 2). This
layer lets an admin list roles, duplicate one into a new custom role, toggle individual permissions
and their data scope, set approval limits, and delete custom roles. The built-in roles
(``DEFAULT_ROLES``) are protected from deletion.
"""
from __future__ import annotations

from django.contrib.auth.models import Group

from erp.audit import services as audit
from erp.core.errors import ValidationError

from . import rbac
from .models import ApprovalLimit, RolePermission
from .roles import DEFAULT_ROLES, SYSTEM_ADMIN


def is_protected(name: str) -> bool:
    return name in DEFAULT_ROLES


def list_roles() -> list[dict]:
    rows = []
    for g in Group.objects.order_by("name"):
        rows.append({
            "name": g.name,
            "protected": is_protected(g.name),
            "members": g.user_set.count(),
            "permission_count": g.role_permissions.count(),
            "modules": _modules_for(g),
        })
    return rows


def role_detail(name: str) -> dict:
    g = _group(name)
    perms = {rp.code: rp.scope for rp in g.role_permissions.all()}
    limits = {al.document_type: al.limit_minor for al in g.approval_limits.all()}
    return {
        "name": g.name,
        "protected": is_protected(g.name),
        "is_admin": g.name == SYSTEM_ADMIN,
        "members": g.user_set.count(),
        "permissions": perms,
        "approval_limits": limits,
        "modules": _modules_for(g),
    }


def create_role(name: str, copy_from: str | None = None, actor=None) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Role name is required")
    if Group.objects.filter(name=name).exists():
        raise ValidationError(f"Role already exists: {name}")
    group = Group.objects.create(name=name)
    if copy_from:
        source = _group(copy_from)
        RolePermission.objects.bulk_create([
            RolePermission(role=group, code=rp.code, scope=rp.scope)
            for rp in source.role_permissions.all()
        ])
        ApprovalLimit.objects.bulk_create([
            ApprovalLimit(role=group, document_type=al.document_type, limit_minor=al.limit_minor)
            for al in source.approval_limits.all()
        ])
    audit.record(module="identity", action="create_role", entity_type="Role",
                 entity_id=name, actor=actor, after={"copy_from": copy_from})
    return role_detail(name)


def set_permission(name: str, code: str, scope: str, granted: bool, actor=None) -> dict:
    g = _group(name)
    if not rbac.is_valid_code(code):
        raise ValidationError(f"Unknown permission: {code}")
    if granted:
        if scope not in {s for s, _ in rbac.SCOPE_CHOICES}:
            raise ValidationError(f"Unknown scope: {scope}")
        RolePermission.objects.update_or_create(role=g, code=code, defaults={"scope": scope})
    else:
        RolePermission.objects.filter(role=g, code=code).delete()
    audit.record(module="identity", action="set_role_permission", entity_type="Role",
                 entity_id=name, actor=actor, after={"code": code, "scope": scope, "granted": granted})
    return role_detail(name)


def set_approval_limit(name: str, document_type: str, limit_minor, actor=None) -> dict:
    g = _group(name)
    if document_type not in rbac.DOCUMENT_TYPES:
        raise ValidationError(f"Unknown document type: {document_type}")
    if limit_minor == "remove":
        ApprovalLimit.objects.filter(role=g, document_type=document_type).delete()
    else:
        # limit_minor may be an int (ceiling) or None (unlimited).
        ApprovalLimit.objects.update_or_create(
            role=g, document_type=document_type, defaults={"limit_minor": limit_minor}
        )
    audit.record(module="identity", action="set_approval_limit", entity_type="Role",
                 entity_id=name, actor=actor, after={"document_type": document_type, "limit_minor": limit_minor})
    return role_detail(name)


def delete_role(name: str, actor=None) -> None:
    if is_protected(name):
        raise ValidationError("Built-in roles cannot be deleted")
    g = _group(name)
    if g.user_set.exists():
        raise ValidationError("Reassign this role's users before deleting it")
    g.delete()
    audit.record(module="identity", action="delete_role", entity_type="Role",
                 entity_id=name, actor=actor)


def registry() -> dict:
    """The vocabulary the role editor renders: modules→entities, actions, scopes, document types."""
    return {
        "modules": rbac.MODULES,
        "actions": rbac.ACTIONS,
        "scopes": [{"value": v, "label": label} for v, label in rbac.SCOPE_CHOICES],
        "document_types": rbac.DOCUMENT_TYPES,
    }


def _group(name: str) -> Group:
    try:
        return Group.objects.get(name=name)
    except Group.DoesNotExist:
        raise ValidationError(f"Unknown role: {name}")


def _modules_for(group: Group) -> list[str]:
    mods = {rbac.module_of(rp.code) for rp in group.role_permissions.all()}
    if group.name == SYSTEM_ADMIN:
        return list(rbac.MODULE_NAMES)
    return [m for m in rbac.MODULE_NAMES if m in mods]
