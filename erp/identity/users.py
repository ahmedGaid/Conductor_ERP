"""User-management service (Increment 3) — admin operations on user accounts.

Thin, auditable functions the admin API delegates to: create/invite, lifecycle changes
(active/invited/suspended/archived), role assignment, password reset, and login history. All writes
record an audit row. ``is_active`` is kept in sync with ``status`` so a suspended/archived user cannot
authenticate even though the account row remains for history.
"""
from __future__ import annotations

import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from erp.audit import services as audit
from erp.core.errors import ValidationError

from .models import (
    USER_ACTIVE,
    USER_ARCHIVED,
    USER_INVITED,
    USER_STATUS_CHOICES,
    USER_SUSPENDED,
    Department,
    Team,
)

User = get_user_model()

_VALID_STATUSES = {s for s, _ in USER_STATUS_CHOICES}
# A user can authenticate only in these states.
_ACTIVE_STATES = {USER_ACTIVE, USER_INVITED}


def _sync_active(user) -> None:
    user.is_active = user.status in _ACTIVE_STATES


def _resolve(model, code):
    if not code:
        return None
    try:
        return model.objects.get(code=code)
    except model.DoesNotExist:
        raise ValidationError(f"Unknown {model.__name__.lower()}: {code}")


def create_user(*, username, email, role=None, branch=None, department=None, team=None, actor=None):
    """Create an invited user with a random temporary password (returned once)."""
    if User.objects.filter(username=username).exists():
        raise ValidationError("Username already taken")
    if User.objects.filter(email=email).exists():
        raise ValidationError("Email already in use")

    temp_password = secrets.token_urlsafe(9)
    user = User(username=username, email=email, status=USER_INVITED, branch=branch)
    user.department = _resolve(Department, department)
    user.team = _resolve(Team, team)
    user.set_password(temp_password)
    _sync_active(user)
    user.save()
    if role:
        user.groups.set([_group(role)])

    audit.record(module="identity", action="create_user", entity_type="User",
                 entity_id=user.pk, actor=actor, after={"username": username, "role": role})
    return user, temp_password


def _group(role_name: str) -> Group:
    try:
        return Group.objects.get(name=role_name)
    except Group.DoesNotExist:
        raise ValidationError(f"Unknown role: {role_name}")


def set_status(user, status: str, actor=None):
    if status not in _VALID_STATUSES:
        raise ValidationError(f"Invalid status: {status}")
    user.status = status
    _sync_active(user)
    user.save(update_fields=["status", "is_active"])
    # Suspending/archiving a user is a real kill-switch: is_active=False already blocks the next
    # request, and revoking their refresh tokens stops any session from renewing.
    if status not in _ACTIVE_STATES:
        from . import sessions
        sessions.revoke_all_sessions(user, actor=actor)
    audit.record(module="identity", action="set_status", entity_type="User",
                 entity_id=user.pk, actor=actor, after={"status": status})
    return user


def assign_role(user, role_name: str, actor=None):
    user.groups.set([_group(role_name)])
    audit.record(module="identity", action="assign_role", entity_type="User",
                 entity_id=user.pk, actor=actor, after={"role": role_name})
    return user


def update_user(user, *, role=None, branch=..., department=None, team=None, status=None,
                display_name=None, job_title=None, phone=None, actor=None):
    if branch is not ...:
        user.branch = branch
    if department is not None:
        user.department = _resolve(Department, department) if department else None
    if team is not None:
        user.team = _resolve(Team, team) if team else None
    if status is not None:
        if status not in _VALID_STATUSES:
            raise ValidationError(f"Invalid status: {status}")
        user.status = status
        _sync_active(user)
    user.save()
    # Personal profile text lives on UserPreferences; a blank value clears the field.
    if display_name is not None or job_title is not None or phone is not None:
        from .models import UserPreferences

        prefs, _created = UserPreferences.objects.get_or_create(user=user)
        if display_name is not None:
            prefs.display_name = display_name
        if job_title is not None:
            prefs.job_title = job_title
        if phone is not None:
            prefs.phone = phone
        prefs.save()
    if role:
        user.groups.set([_group(role)])
    audit.record(module="identity", action="update_user", entity_type="User",
                 entity_id=user.pk, actor=actor)
    return user


def reset_password(user, actor=None) -> str:
    """Set a fresh random temporary password and return it once."""
    temp_password = secrets.token_urlsafe(9)
    user.set_password(temp_password)
    user.save(update_fields=["password"])
    audit.record(module="identity", action="reset_password", entity_type="User",
                 entity_id=user.pk, actor=actor)
    return temp_password


def login_history(user, limit: int = 25):
    """Recent login-related audit rows for a user (the 'Sessions' view).

    JWT is stateless, so this is the authoritative record of access. True per-device revocation needs
    the simplejwt token-blacklist app and is deferred; suspending the user blocks new access today.
    """
    from erp.audit.models import AuditEntry

    return list(
        AuditEntry.objects.filter(
            entity_type="User", entity_id=str(user.pk), action__startswith="login"
        ).order_by("-created_at")[:limit]
    )


def _prefs(user):
    from .models import UserPreferences

    return UserPreferences.objects.filter(user=user).first()


def serialize_list(user) -> dict:
    """The compact shape for the Users table."""
    p = _prefs(user)
    roles = user.roles
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": (p.display_name if p else "") or user.username,
        "role": roles[0] if roles else None,
        "roles": roles,
        "branch": user.branch.code if user.branch_id else None,
        "department": user.department.code if user.department_id else None,
        "status": user.status,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def serialize_detail(user) -> dict:
    """The full profile: identity + role + module access + effective permissions + sessions + audit."""
    from . import access, sessions as sessions_svc

    p = _prefs(user)
    data = serialize_list(user)
    data.update({
        "job_title": p.job_title if p else "",
        "phone": p.phone if p else "",
        "team": user.team.code if user.team_id else None,
        "is_2fa_enabled": user.is_2fa_enabled,
        "modules": access.accessible_modules(user),
        "permissions": [
            {"code": c, "scope": s} for c, s in sorted(access.user_permissions(user).items())
        ],
        "sessions": [
            {"action": e.action, "at": e.created_at.isoformat(), "result": e.result,
             "correlation_id": e.correlation_id}
            for e in login_history(user)
        ],
        "active_sessions": sessions_svc.active_sessions(user),
        "audit": _recent_actions(user),
    })
    return data


def _recent_actions(user, limit: int = 25) -> list[dict]:
    """Recent audit rows where this user was the actor (the user's own activity log)."""
    from erp.audit.models import AuditEntry

    rows = AuditEntry.objects.filter(actor=user).order_by("-created_at")[:limit]
    return [
        {"module": e.module, "action": e.action, "entity_type": e.entity_type,
         "entity_id": e.entity_id, "at": e.created_at.isoformat(), "result": e.result}
        for e in rows
    ]


def bulk(action: str, user_ids: list, *, role=None, actor=None) -> int:
    """Apply a bulk action to many users; returns the count affected."""
    users = list(User.objects.filter(pk__in=user_ids))
    for u in users:
        if action == "suspend":
            set_status(u, USER_SUSPENDED, actor=actor)
        elif action == "activate":
            set_status(u, USER_ACTIVE, actor=actor)
        elif action == "archive":
            set_status(u, USER_ARCHIVED, actor=actor)
        elif action == "assign_role":
            assign_role(u, role, actor=actor)
        else:
            raise ValidationError(f"Unknown bulk action: {action}")
    return len(users)
