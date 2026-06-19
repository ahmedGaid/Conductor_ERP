"""Public contract — the sanctioned way another module sends a notification directly.

Most notifications are driven by domain events (see ``handlers``); this is for the rare case a module
wants to send one explicitly without importing notifications internals.
"""
from __future__ import annotations

from ..domain.models import NotificationChannel  # noqa: F401


def notify(*, channel: str, recipient: str, subject: str = "", body: str = "",
           reference: str = "", actor=None):
    from ..services import dispatch
    return dispatch(channel=channel, recipient=recipient, subject=subject, body=body,
                    reference=reference, actor=actor)


__all__ = ["notify", "NotificationChannel"]
