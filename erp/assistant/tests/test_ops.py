"""Ops view (ai-reliability T1.8): aggregation math over Trace/TraceStep + admin-only RBAC."""
from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from erp.assistant.models import Trace, TraceStep
from erp.identity.models import User

pytestmark = pytest.mark.django_db

SUMMARY_URL = "/api/assistant/ops/summary"
TRACES_URL = "/api/assistant/ops/traces"


def _admin(username: str = "ops_admin") -> APIClient:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
        is_superuser=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _plain(username: str = "ops_plain") -> APIClient:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _trace(**kw) -> Trace:
    defaults = dict(
        feature=Trace.Feature.ASK, provider="anthropic", model="claude-opus-4-8",
        input_tokens=100, output_tokens=50, latency_ms=200, cost_microcents=10,
        status=Trace.Status.OK,
    )
    defaults.update(kw)
    return Trace.objects.create(**defaults)


def _backdate(trace: Trace, days_ago: int) -> Trace:
    Trace.objects.filter(pk=trace.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=days_ago)
    )
    trace.refresh_from_db()
    return trace


# --- RBAC ------------------------------------------------------------------------------------

def test_non_admin_gets_403_on_both_endpoints():
    client = _plain()
    assert client.get(SUMMARY_URL).status_code == 403
    assert client.get(TRACES_URL).status_code == 403


def test_admin_gets_200():
    client = _admin()
    assert client.get(SUMMARY_URL).status_code == 200
    assert client.get(TRACES_URL).status_code == 200


# --- summary aggregation -----------------------------------------------------------------------

def test_summary_totals_error_rate_tokens_and_cost():
    _trace(input_tokens=100, output_tokens=50, cost_microcents=30, latency_ms=100,
           status=Trace.Status.OK)
    _trace(input_tokens=200, output_tokens=100, cost_microcents=70, latency_ms=300,
           status=Trace.Status.ERROR, error_class="ProviderError")

    resp = _admin().get(SUMMARY_URL)
    data = resp.json()["data"]
    assert data["total_calls"] == 2
    assert data["error_rate"] == pytest.approx(0.5)
    assert data["input_tokens"] == 300
    assert data["output_tokens"] == 150
    assert data["cost_microcents"] == 100
    assert data["top_error_classes"] == [{"error_class": "ProviderError", "count": 1}]
    assert data["latency_ms"]["p50"] in (100, 300)


def test_summary_excludes_traces_outside_the_day_window():
    recent = _trace()
    old = _backdate(_trace(), days_ago=30)

    resp = _admin().get(f"{SUMMARY_URL}?days=7")
    data = resp.json()["data"]
    assert data["total_calls"] == 1


def test_summary_daily_breakdown_by_feature():
    _trace(feature=Trace.Feature.ASK)
    _trace(feature=Trace.Feature.AGENT)

    resp = _admin().get(SUMMARY_URL)
    daily = resp.json()["data"]["daily"]
    assert len(daily) == 1
    assert daily[0]["count"] == 2
    assert daily[0]["by_feature"] == {"ask": 1, "agent": 1}


def test_summary_days_param_is_clamped():
    resp = _admin().get(f"{SUMMARY_URL}?days=9999")
    assert resp.status_code == 200
    assert resp.json()["data"]["days"] == 90


# --- traces list -------------------------------------------------------------------------------

def test_traces_list_includes_steps_and_actor():
    admin_client = _admin("ops_actor_admin")
    actor = User.objects.get(username="ops_actor_admin")
    trace = Trace.objects.create(feature=Trace.Feature.AGENT, actor=actor, status=Trace.Status.OK)
    TraceStep.objects.create(trace=trace, seq=0, kind=TraceStep.Kind.LLM, name="round1", ok=True)
    TraceStep.objects.create(trace=trace, seq=1, kind=TraceStep.Kind.TOOL, name="low_stock", ok=True)

    resp = admin_client.get(TRACES_URL)
    rows = resp.json()["data"]["results"]
    assert len(rows) == 1
    assert rows[0]["actor"] == {"id": actor.id, "username": actor.username}
    assert [s["kind"] for s in rows[0]["steps"]] == ["llm", "tool"]


def test_traces_list_filters_by_feature_and_status():
    _trace(feature=Trace.Feature.ASK, status=Trace.Status.OK)
    _trace(feature=Trace.Feature.AGENT, status=Trace.Status.ERROR)
    client = _admin()

    resp = client.get(f"{TRACES_URL}?feature=agent")
    rows = resp.json()["data"]["results"]
    assert len(rows) == 1
    assert rows[0]["feature"] == "agent"

    resp = client.get(f"{TRACES_URL}?status=error")
    rows = resp.json()["data"]["results"]
    assert len(rows) == 1
    assert rows[0]["status"] == "error"


def test_traces_list_pagination():
    for _ in range(5):
        _trace()

    resp = _admin().get(f"{TRACES_URL}?page=1&page_size=2")
    data = resp.json()["data"]
    assert data["count"] == 5
    assert len(data["results"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
