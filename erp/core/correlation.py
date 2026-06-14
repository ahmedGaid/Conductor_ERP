"""Correlation ID propagation.

A correlation ID is generated at every entry point (HTTP request, Celery job, import/export,
report run) and must flow into logs, errors, audit records, and monitoring. It is stored in a
context variable so any code in the same execution context can read it without threading it
through every call.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

HEADER_NAME = "X-Correlation-ID"

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


@contextmanager
def correlation_scope(value: str | None = None) -> Iterator[str]:
    """Bind a correlation ID for the duration of a block (used by Celery tasks/jobs)."""
    cid = value or new_correlation_id()
    token = _correlation_id.set(cid)
    try:
        yield cid
    finally:
        _correlation_id.reset(token)
