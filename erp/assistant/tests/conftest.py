"""Shared fixtures for erp.assistant tests."""
from __future__ import annotations

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_assistant_cache():
    """Circuit-breaker state (T2.3, gateway/breaker.py) lives in Django's cache, which — unlike the
    DB — is NOT reset between tests. Clear it so one test's provider failures can never leak into
    another test's breaker state (both are keyed only by provider name, e.g. "anthropic")."""
    cache.clear()
    yield
    cache.clear()
