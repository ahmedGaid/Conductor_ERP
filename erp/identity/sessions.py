"""Session management — list and revoke a user's active sign-ins (refresh tokens).

With the simplejwt ``token_blacklist`` app installed, every issued **refresh** token is tracked as an
``OutstandingToken``. A login = one outstanding token = one "session" (one device/browser). Revoking
a session blacklists its refresh token, so that device can no longer renew access; combined with the
``is_active`` check on every request (a suspended user is rejected immediately), this turns "suspend"
into a real kill-switch and lets an admin sign a single device out.

Note: an access token is stateless and lives up to ``ACCESS_TOKEN_LIFETIME`` (30 min). Revoking a
session stops renewal immediately but an already-issued access token remains valid until it expires;
suspending the user blocks even that on the next request. True per-request access revocation would
need a server-side access-token check and is out of scope here.
"""
from __future__ import annotations

from django.utils import timezone

from erp.audit import services as audit


def _models():
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    return OutstandingToken, BlacklistedToken


def active_sessions(user) -> list[dict]:
    """The user's non-revoked, non-expired refresh tokens — one row per live session."""
    OutstandingToken, BlacklistedToken = _models()
    revoked_ids = set(
        BlacklistedToken.objects.filter(token__user=user).values_list("token_id", flat=True)
    )
    now = timezone.now()
    rows = (
        OutstandingToken.objects.filter(user=user, expires_at__gt=now)
        .exclude(id__in=revoked_ids)
        .order_by("-created_at")
    )
    return [
        {
            "id": t.id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
        }
        for t in rows
    ]


def revoke_session(user, token_id: int, actor=None) -> bool:
    """Blacklist one of the user's refresh tokens. Returns False if it isn't theirs / not found."""
    OutstandingToken, BlacklistedToken = _models()
    token = OutstandingToken.objects.filter(id=token_id, user=user).first()
    if token is None:
        return False
    BlacklistedToken.objects.get_or_create(token=token)
    audit.record(module="identity", action="revoke_session", entity_type="User",
                 entity_id=user.pk, actor=actor, after={"token_id": token_id})
    return True


def revoke_all_sessions(user, actor=None) -> int:
    """Blacklist every outstanding refresh token for the user (force sign-out everywhere).

    Returns the number of sessions newly revoked.
    """
    OutstandingToken, BlacklistedToken = _models()
    count = 0
    for token in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        if created:
            count += 1
    if count:
        audit.record(module="identity", action="revoke_all_sessions", entity_type="User",
                     entity_id=user.pk, actor=actor, after={"revoked": count})
    return count
