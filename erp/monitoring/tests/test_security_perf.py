"""Phase 10 hardening — DRF rate limiting + query/latency budgets on hot list endpoints.

Throttling is disabled in dev/test settings (so the rest of the suite isn't rate-limited); the last
test re-enables a tiny rate via override_settings to prove the mechanism actually blocks abuse.

Perf budgets (session 01, recorded in DECISIONS.md "Perf budgets 2026-07"): every hot list endpoint
serializes N rows in a **constant** number of queries (≤ LIST_QUERY_BUDGET, no N+1) and answers in
p95 < LIST_P95_MS on seed-sized data. Budget tests run before any throttle override.
"""
from __future__ import annotations

import time
from decimal import Decimal

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

# Hot list endpoints must serialize N rows in a constant number of queries: auth/scope lookups +
# the main query + one query per prefetch — never a query per row.
LIST_QUERY_BUDGET = 8
# p95 wall-clock budget per list call on seed-sized data (test client, local DB).
LIST_P95_MS = 150.0


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
    with django_assert_max_num_queries(LIST_QUERY_BUDGET):
        res = client.get("/api/accounting/journals")
    assert res.status_code == 200
    assert len(res.data["data"]) == 6


def _seed_orders(n: int) -> None:
    from erp.sales.domain.models import Customer, SalesOrder, SalesOrderLine

    customer = Customer.objects.create(code="C-PERF", name="Perf customer")
    for i in range(n):
        order = SalesOrder.objects.create(
            number=f"SO-PERF-{i:04d}", customer=customer, order_date="2026-06-15",
            warehouse_code="WH-1", subtotal_minor=15_000,
        )
        for ln in range(1, 4):
            SalesOrderLine.objects.create(
                order=order, line_no=ln, item_sku=f"SKU-{ln}", quantity=Decimal("1"),
                unit_price_minor=5_000, line_total_minor=5_000,
            )


def _seed_movements(n: int) -> None:
    from erp.inventory.domain.models import Item, MovementType, StockBalance, StockMovement, Warehouse

    item = Item.objects.create(sku="SKU-PERF", name="Perf item")
    warehouse = Warehouse.objects.create(code="WH-PERF", name="Perf warehouse")
    for i in range(n):
        StockMovement.objects.create(
            item=item, warehouse=warehouse, type=MovementType.RECEIPT, date="2026-06-15",
            quantity=Decimal("1"), unit_cost_minor=1_000, value_minor=1_000, reference=f"REF-{i}",
        )
    StockBalance.objects.create(item=item, warehouse=warehouse, quantity=Decimal(n), value_minor=n * 1_000)


def test_orders_list_query_count_is_bounded(django_assert_max_num_queries):
    """Serializing N orders (+ their lines) must stay O(1) queries — guards the lines prefetch.

    A stray .order_by()/.filter() on the prefetched lines would clone the queryset, bypass the
    prefetch cache, and reintroduce a query per row — this budget catches that.
    """
    client = _admin_client()
    _seed_orders(6)
    with django_assert_max_num_queries(LIST_QUERY_BUDGET):
        res = client.get("/api/sales/orders")
    assert res.status_code == 200
    assert len(res.data["data"]) == 6
    assert all(len(row["lines"]) == 3 for row in res.data["data"])


def test_movements_list_query_count_is_bounded(django_assert_max_num_queries):
    client = _admin_client()
    _seed_movements(6)
    with django_assert_max_num_queries(LIST_QUERY_BUDGET):
        res = client.get("/api/inventory/movements")
    assert res.status_code == 200
    assert len(res.data["data"]) == 6


def test_stock_on_hand_query_count_is_bounded(django_assert_max_num_queries):
    client = _admin_client()
    _seed_movements(6)
    with django_assert_max_num_queries(LIST_QUERY_BUDGET):
        res = client.get("/api/inventory/reports/stock-on-hand")
    assert res.status_code == 200
    assert len(res.data["data"]["rows"]) == 1


def test_orders_list_p95_latency_under_budget():
    """p95 of 20 list calls must beat the latency budget — catches gross slowdowns, not jitter."""
    client = _admin_client()
    _seed_orders(6)
    client.get("/api/sales/orders")  # warm-up: first call pays connection/auth setup
    samples: list[float] = []
    for _ in range(20):
        t0 = time.perf_counter()
        res = client.get("/api/sales/orders")
        samples.append((time.perf_counter() - t0) * 1000)
        assert res.status_code == 200
    samples.sort()
    p95 = samples[int(len(samples) * 0.95) - 1]
    assert p95 < LIST_P95_MS, f"orders list p95 {p95:.1f}ms exceeds {LIST_P95_MS}ms budget"


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
