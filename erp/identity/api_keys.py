"""API key admin service (TH FILE_14, Task A) — create/revoke/list, admin-only.

A key is never broader than the role it carries: creating one binds an auto-created, hidden
"principal" user (unusable password, never a human, excluded from the Users admin list) to the
chosen role's group, so every existing RBAC/scoping/audit path treats key traffic exactly like a
human login carrying that role — no parallel permission logic to keep in sync.
"""
from __future__ import annotations

import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from erp.audit import services as audit
from erp.core.errors import PermissionError, ValidationError

from . import access
from .authentication import hash_secret
from .models import USER_ACTIVE, ApiKey

User = get_user_model()

_PREFIX_ATTEMPTS = 5


def _require_admin(actor) -> None:
    if not access.is_superadmin(actor):
        raise PermissionError("Only an admin may manage API keys")


def _group(role_name: str) -> Group:
    try:
        return Group.objects.get(name=role_name)
    except Group.DoesNotExist:
        raise ValidationError(f"Unknown role: {role_name}") from None


def _new_prefix() -> str:
    for _ in range(_PREFIX_ATTEMPTS):
        prefix = secrets.token_hex(4)
        if not ApiKey.objects.filter(prefix=prefix).exists():
            return prefix
    raise ValidationError("Could not allocate a unique API key prefix")


def _create_principal(name: str, prefix: str, group: Group):
    principal = User(
        username=f"apikey:{prefix}",
        email=f"apikey+{prefix}@keys.internal",
        status=USER_ACTIVE,
        is_active=True,
    )
    principal.set_unusable_password()
    principal.save()
    principal.groups.set([group])
    return principal


def create_key(name: str, role_name: str, *, expires_at=None, actor=None) -> tuple[ApiKey, str]:
    """Create a key bound to ``role_name``. Returns ``(row, raw_secret)`` — the secret is shown
    exactly once by the caller; only its hash is ever persisted."""
    _require_admin(actor)
    name = (name or "").strip()
    if not name:
        raise ValidationError("Key name is required")
    group = _group(role_name)

    prefix = _new_prefix()
    raw_secret = f"ck_{prefix}_{secrets.token_urlsafe(32)}"
    principal = _create_principal(name, prefix, group)

    api_key = ApiKey.objects.create(
        name=name,
        prefix=prefix,
        hashed_key=hash_secret(raw_secret),
        role=group,
        principal=principal,
        created_by=actor if getattr(actor, "pk", None) else None,
        expires_at=expires_at,
    )
    audit.record(module="identity", action="create_api_key", entity_type="ApiKey",
                 entity_id=api_key.pk, actor=actor, after={"name": name, "role": role_name})
    return api_key, raw_secret


def revoke_key(pk: int, actor=None) -> ApiKey:
    _require_admin(actor)
    api_key = _get(pk)
    api_key.is_active = False
    api_key.save(update_fields=["is_active"])
    audit.record(module="identity", action="revoke_api_key", entity_type="ApiKey",
                 entity_id=api_key.pk, actor=actor, after={"name": api_key.name})
    return api_key


def list_keys(actor=None) -> list[dict]:
    _require_admin(actor)
    return [serialize(k) for k in ApiKey.objects.select_related("role").order_by("-created_at")]


def serialize(api_key: ApiKey) -> dict:
    return {
        "id": api_key.pk,
        "name": api_key.name,
        "prefix": api_key.prefix,
        "role": api_key.role.name,
        "created_at": api_key.created_at.isoformat(),
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "is_active": api_key.is_active,
    }


def _get(pk: int) -> ApiKey:
    try:
        return ApiKey.objects.get(pk=pk)
    except ApiKey.DoesNotExist:
        raise ValidationError(f"Unknown API key: {pk}") from None
