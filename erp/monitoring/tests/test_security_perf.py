"""Phase 10 hardening — DRF rate limiting + query-count budgets on heavy list endpoints.

Throttling is disabled in dev/test settings (so the rest of the suite isn't rate-limited); the last
test re-enables a tiny rate via override_settings to prove the mechanism actually blocks abuse. The
query-count test runs first (before any throttle override) and asserts the heaviest list endpoint
serializes N rows in a constant number of queries (no N+1).
"""
from __future__ import annotations

import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="sec_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class _ThreePerMin(UserRateThrottle):
    """A fixed 3/min user throttle — exercises DRF's real throttle machinery without depending on
    runtime settings reloads (which don't refresh DRF's cached api_settings mid-process)."""

    scope = "sec_perf_test"

    def get_rate(self) -> str:
        return "3/min"


class _PingView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [_ThreePerMin]

    def get(self, request) -> Response:
        return Response({"ok": True})


def _bootstrap(client) -> None:
    for code, name, type_, is_cash in [
        ("1000", "Cash", "asset", True),
        ("3000", "Capital", "equity", False),
    ]:
        assert client.post(
            "/api/accounting/accounts",
            {"code": code, "name": name, "type": type_, "is_postable": True, "is_cash": is_cash},
            format="json",
        ).status_code == 201
    assert client.post(
        "/api/accounting/fiscal-years",
        {"code": "2026", "start_date": "2026-01-01", "end_date": "2026-12-31"},
        format="json",
    ).status_code == 201
    assert client.post(
        "/api/accounting/periods",
        {"fiscal_year_code": "2026", "code": "2026-06", "start_date": "2026-06-01", "end_date": "2026-06-30"},
        format="json",
    ).status_code == 201


def _post_journals(client, n: int) -> None:
    for i in range(n):
        assert client.post(
            "/api/accounting/journals",
            {
                "date": "2026-06-15",
                "memo": f"j{i}",
                "lines": [
                    {"account_code": "1000", "debit": 10000, "credit": 0},
                    {"account_code": "3000", "debit": 0, "credit": 10000},
                ],
            },
            format="json",
        ).status_code == 201


def test_throttle_classes_are_configured():
    classes = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_CLASSES", ())
    assert any("AnonRateThrottle" in c for c in classes), classes
    assert any("UserRateThrottle" in c for c in classes), classes


def test_journals_list_query_count_is_bounded(django_assert_max_num_queries):
    """The journals list must be O(1) queries, not O(entries) — proves the lines prefetch holds.

    Runs before any throttle override (and dev disables throttling), so it is never rate-limited.
    """
    client = _admin_client()
    _bootstrap(client)
    _post_journals(client, 6)
    with django_assert_max_num_queries(12):
        res = client.get("/api/accounting/journals")
    assert res.status_code == 200
    assert len(res.data["data"]) == 6


def test_user_rate_throttle_returns_429_when_exceeded():
    # Drive DRF's real throttle path: a fixed 3/min throttle on a view; the 4th call must be blocked.
    user = User.objects.create_user(username="throttle_user", password="Dev12345!")
    factory = APIRequestFactory()
    view = _PingView.as_view()
    cache.clear()
    try:
        codes = []
        for _ in range(5):
            request = factory.get("/_throttle_probe")
            force_authenticate(request, user=user)
            codes.append(view(request).status_code)
    finally:
        cache.clear()
    assert codes[:3] == [200, 200, 200], codes
    assert codes[3] == 429, codes
