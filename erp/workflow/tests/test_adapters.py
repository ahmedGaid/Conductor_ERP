"""Adapter tests: SQL parameterization + DB dedupe, REST mapping/header, factory."""
from __future__ import annotations

import io

import pytest
from django.db import connection

from erp.workflow.adapters import get_adapter
from erp.workflow.adapters.rest import RestAdapter
from erp.workflow.adapters.sql import SqlAdapter
from erp.workflow.adapters.types import AdapterCall

pytestmark = pytest.mark.django_db


def test_factory_returns_kinds_and_rejects_unknown():
    assert get_adapter("rest").kind == "rest"
    assert get_adapter("sql").kind == "sql"
    assert get_adapter("webhook").kind == "webhook"
    with pytest.raises(ValueError):
        get_adapter("nope")


def test_sql_parameterized_select_is_inert_to_injection():
    adapter = SqlAdapter()
    # The malicious string is bound as a parameter, never interpreted as SQL.
    evil = "1); DROP TABLE erp_external.purchase_orders; --"
    res = adapter.call(AdapterCall(config={"statement": "SELECT %s AS echo", "params": [evil]}))
    assert res.ok is True
    assert res.data == [{"echo": evil}]
    # Table still exists.
    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM erp_external.purchase_orders")
        assert cur.fetchone()[0] >= 0


def test_sql_on_conflict_dedupes_same_key():
    adapter = SqlAdapter()
    stmt = (
        "INSERT INTO erp_external.purchase_orders (id, request_ref, amount, supplier, idempotency_key)"
        " VALUES (%s,%s,%s,%s,%s) ON CONFLICT (idempotency_key) DO NOTHING"
    )
    params = ["PO-DEDUP", "PR-9", 10, "ACME", "KEY-DEDUP"]
    adapter.call(AdapterCall(config={"statement": stmt, "params": params}))
    adapter.call(AdapterCall(config={"statement": stmt, "params": params}))  # same key
    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM erp_external.purchase_orders WHERE idempotency_key=%s", ["KEY-DEDUP"])
        assert cur.fetchone()[0] == 1


class _FakeResp:
    def __init__(self, status, body):
        self.status = status
        self._body = body.encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_rest_forwards_idempotency_key_and_maps_status(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["headers"] = req.headers
        captured["method"] = req.get_method()
        return _FakeResp(201, '{"ok": true}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    res = RestAdapter().call(
        AdapterCall(
            config={"method": "POST", "url": "http://x/po", "body": {"a": 1}},
            idempotency_key="KEY-1",
        )
    )
    assert res.ok is True and res.status == 201
    # urllib title-cases header keys.
    assert captured["headers"].get("Idempotency-key") == "KEY-1"
    assert captured["method"] == "POST"


def test_rest_maps_5xx_to_not_ok(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeResp(500, "boom")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    res = RestAdapter().call(AdapterCall(config={"method": "GET", "url": "http://x"}))
    assert res.ok is False and res.status == 500
