"""Anthropic client seam.

Single construction point so (a) tests monkeypatch ``get_client`` and gates never make live
calls, and (b) an install without the ``anthropic`` package or an API key still runs — the
assistant is optional and everything checks ``enabled()`` first.
"""
from __future__ import annotations

from django.conf import settings


def enabled() -> bool:
    return bool(getattr(settings, "ASSISTANT_ENABLED", False))


def get_client():
    import anthropic  # deferred: package is only needed when the assistant is enabled

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
