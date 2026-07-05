"""The in-app inbox — a per-user reader over the notification log.

An in-app notification is a normal ``Notification`` row on the ``inapp`` channel whose ``recipient``
is a username. These helpers read and mark *your own* rows only (isolation is by username), so one
user never sees or clears another's inbox. Ordering is unread-first, newest-first — the calm surface
puts what still needs a glance at the top without a red count.
"""
from __future__ import annotations

from django.db.models import Case, IntegerField, QuerySet, Value, When
from django.utils import timezone

from ..domain.models import Notification, NotificationChannel

# The inbox is a glance, not an archive — cap the panel so it never becomes an unbounded list.
INBOX_LIMIT = 50


def _username(user) -> str:
    return user.get_username() if user is not None else ""


def inbox_for(user) -> QuerySet[Notification]:
    """This user's in-app notifications, unread first then newest first, capped."""
    username = _username(user)
    if not username:
        return Notification.objects.none()
    return (
        Notification.objects.filter(channel=NotificationChannel.INAPP, recipient=username)
        .annotate(
            _unread=Case(
                When(read_at__isnull=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("_unread", "-created_at")[:INBOX_LIMIT]
    )


def mark_read(user, note_id) -> Notification | None:
    """Mark one of this user's in-app rows read. Returns the row, or ``None`` if it isn't theirs."""
    note = (
        Notification.objects.filter(
            id=note_id, channel=NotificationChannel.INAPP, recipient=_username(user)
        )
        .first()
    )
    if note is None:
        return None
    if note.read_at is None:
        note.read_at = timezone.now()
        note.save(update_fields=["read_at", "updated_at"])
    return note


def mark_all_read(user) -> int:
    """Mark every unread in-app row of this user's read. Returns how many were flipped."""
    return (
        Notification.objects.filter(
            channel=NotificationChannel.INAPP, recipient=_username(user), read_at__isnull=True
        )
        .update(read_at=timezone.now())
    )
