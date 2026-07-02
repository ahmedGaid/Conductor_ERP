"""Natural-language assistant — mocked model, no live calls in gates.

The model is a two-step JSON exchange (route → answer). We monkeypatch the single ``complete_json``
seam to return canned route/answer dicts in order, so every test exercises the real routing, the
real scoped tool call, real server-side money formatting, and real citation building — only the
network hop to the provider is faked.
"""
from __future__ import annotations

import datetime

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.errors import AssistantUnavailableError
from erp.assistant.services import ask
from erp.audit.models import AuditEntry
from erp.identity.models import User
from erp.sales.domain.models import Customer, SalesOrder

pytestmark = pytest.mark.django_db

ASK_URL = "/api/assistant/ask"


def _client() -> APIClient:
    user = User.objects.create_user(username="ai_asker", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _replies(monkeypatch, *canned: dict):
    """Make ``complete_json`` return each canned dict in turn (route, then answer)."""
    seq = list(canned)

    def fake(system, user, schema, **_):
        return seq.pop(0)

    monkeypatch.setattr(ask, "complete_json", fake)


def _order(number: str, *, subtotal: int, invoiced: int = 0, paid: int = 0, status: str = "confirmed"):
    customer, _ = Customer.objects.get_or_create(code="C-1", defaults={"name": "Nile Traders"})
    return SalesOrder.objects.create(
        number=number, customer=customer, order_date=datetime.date.today(),
        warehouse_code="WH-1", status=status,
        subtotal_minor=subtotal, invoiced_minor=invoiced, paid_minor=paid,
    )


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_ask_routes_to_sales_summary_and_answers(monkeypatch):
    _order("SO-1", subtotal=100_00)
    _order("SO-2", subtotal=250_00)
    _replies(
        monkeypatch,
        {"tool": "sales_summary", "period": "this_month", "query": None, "limit": None},
        {"answer": "مبيعات هذا الشهر ٣٥٠٫٠٠ جنيه."},
    )

    resp = _client().post(ASK_URL, {"question": "كم مبيعات هذا الشهر؟"}, format="json")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["used_tool"] == "sales_summary"
    assert "٣٥٠" in data["answer"]
    assert data["citations"] == []

    entry = AuditEntry.objects.get(module="assistant", action="ask")
    assert entry.after["tool"] == "sales_summary"
    assert entry.actor is not None


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_the_summary_number_comes_from_the_data_not_the_model(monkeypatch):
    _order("SO-1", subtotal=100_00)
    _order("SO-2", subtotal=250_00)
    calls: list[str] = []

    def fake(system, user, schema, **_):
        calls.append(user)
        if len(calls) == 1:  # first call = route
            return {"tool": "sales_summary", "period": "this_month", "query": None, "limit": None}
        return {"answer": "ok"}  # second call = answer

    monkeypatch.setattr(ask, "complete_json", fake)
    resp = _client().post(ASK_URL, {"question": "sales this month"}, format="json")
    assert resp.status_code == 200
    # 100.00 + 250.00 = 350.00 EGP, formatted server-side and handed to the model verbatim.
    assert "350.00 EGP" in calls[1]


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_find_orders_builds_real_citations(monkeypatch):
    o = _order("SO-77", subtotal=500_00)
    _replies(
        monkeypatch,
        {"tool": "find_orders", "period": None, "query": "SO-77", "limit": None},
        {"answer": "لقيت أمر بيع واحد."},
    )
    resp = _client().post(ASK_URL, {"question": "find order SO-77"}, format="json")
    assert resp.status_code == 200
    citations = resp.json()["data"]["citations"]
    assert citations == [{"type": "order", "value": str(o.id), "label": "SO-77"}]


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_no_matching_tool_still_answers_without_running_one(monkeypatch):
    _replies(
        monkeypatch,
        {"tool": "none", "period": None, "query": None, "limit": None},
        {"answer": "أقدر أساعدك في المبيعات والمخزون والتحصيل."},
    )
    resp = _client().post(ASK_URL, {"question": "مرحبا"}, format="json")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["used_tool"] is None
    assert data["citations"] == []
    assert data["answer"]


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_upstream_failure_is_502_with_catalog_code(monkeypatch):
    def boom(*a, **k):
        raise AssistantUnavailableError(data={"reason": "RuntimeError"})

    monkeypatch.setattr(ask, "complete_json", boom)
    resp = _client().post(ASK_URL, {"question": "كم مبيعات هذا الشهر؟"}, format="json")
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "AI-002"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_blank_and_overlong_questions_are_rejected():
    client = _client()
    assert client.post(ASK_URL, {"question": "   "}, format="json").status_code == 400
    long_q = "أ" * (ask.MAX_QUESTION_CHARS + 1)
    assert client.post(ASK_URL, {"question": long_q}, format="json").status_code == 400


@override_settings(ASSISTANT_ENABLED=False)
def test_disabled_endpoint_is_404():
    assert _client().post(ASK_URL, {"question": "hi"}, format="json").status_code == 404
