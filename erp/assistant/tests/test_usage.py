"""Monthly usage endpoint (twenty-harvest FILE_20 Task A): month-window aggregation over Trace +
budget/spend records, admin-only RBAC."""
from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from erp.assistant.models import Budget, SpendRollup, Trace, TraceStep
from erp.identity.models import User

pytestmark = pytest.mark.django_db

USAGE_URL = "/api/assistant/usage"


def _admin(username: str = "usage_admin") -> APIClient:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
        is_superuser=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _plain(username: str = "usage_plain") -> APIClient:
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


def _at(trace: Trace, when) -> Trace:
    Trace.objects.filter(pk=trace.pk).update(created_at=when)
    trace.refresh_from_db()
    return trace


def _this_month_start():
    return timezone.localdate().replace(day=1)


def _mid_this_month():
    return timezone.make_aware(
        timezone.datetime.combine(_this_month_start().replace(day=15), timezone.datetime.min.time())
    )


# --- RBAC ----------------------------------------------------------------------------------

def test_non_admin_gets_403():
    assert _plain().get(USAGE_URL).status_code == 403


def test_admin_gets_200():
    assert _admin().get(USAGE_URL).status_code == 200


# --- month window ----------------------------------------------------------------------------

def test_defaults_to_current_month_and_totals_aggregate():
    _at(_trace(input_tokens=100, output_tokens=50, cost_microcents=30), _mid_this_month())
    _at(_trace(input_tokens=200, output_tokens=100, cost_microcents=70), _mid_this_month())

    resp = _admin().get(USAGE_URL)
    data = resp.json()["data"]
    assert data["month"] == _this_month_start().strftime("%Y-%m")
    assert data["totals"]["requests"] == 2
    assert data["totals"]["input_tokens"] == 300
    assert data["totals"]["output_tokens"] == 150
    assert data["totals"]["cost_microcents"] == 100


def test_month_param_selects_a_different_month_and_excludes_others():
    last_month_start = (_this_month_start().replace(day=1) - timezone.timedelta(days=1)).replace(day=1)
    in_range = _at(_trace(cost_microcents=5), timezone.make_aware(
        timezone.datetime.combine(last_month_start.replace(day=10), timezone.datetime.min.time())))
    out_of_range = _at(_trace(cost_microcents=9), _mid_this_month())

    resp = _admin().get(f"{USAGE_URL}?month={last_month_start.strftime('%Y-%m')}")
    data = resp.json()["data"]
    assert data["totals"]["requests"] == 1
    assert data["totals"]["cost_microcents"] == 5


def test_invalid_month_param_is_rejected():
    resp = _admin().get(f"{USAGE_URL}?month=not-a-month")
    assert resp.status_code == 400


# --- provider / user splits --------------------------------------------------------------------

def test_by_provider_split_and_unknown_bucket():
    _at(_trace(provider="anthropic", cost_microcents=10), _mid_this_month())
    _at(_trace(provider="gemini", cost_microcents=20), _mid_this_month())
    _at(_trace(provider="", cost_microcents=1), _mid_this_month())

    resp = _admin().get(USAGE_URL)
    by_provider = {r["provider"]: r for r in resp.json()["data"]["by_provider"]}
    assert by_provider["anthropic"]["cost_microcents"] == 10
    assert by_provider["gemini"]["cost_microcents"] == 20
    assert by_provider["unknown"]["cost_microcents"] == 1
    assert sum(r["requests"] for r in by_provider.values()) == 3


def test_by_user_table_excludes_anonymous_traces():
    admin_client = _admin("usage_actor_admin")
    actor = User.objects.get(username="usage_actor_admin")
    _at(_trace(actor=actor, cost_microcents=15), _mid_this_month())
    _at(_trace(actor=None, cost_microcents=99), _mid_this_month())  # system-triggered, no user

    resp = admin_client.get(USAGE_URL)
    data = resp.json()["data"]
    assert data["totals"]["requests"] == 2  # both still counted in totals
    assert len(data["by_user"]) == 1
    assert data["by_user"][0]["username"] == "usage_actor_admin"
    assert data["by_user"][0]["cost_microcents"] == 15


# --- cache-hit share -------------------------------------------------------------------------

def test_cache_hit_share_zero_when_no_cache_task_lookups():
    _at(_trace(feature=Trace.Feature.ASK), _mid_this_month())
    resp = _admin().get(USAGE_URL)
    assert resp.json()["data"]["totals"]["cache_hit_share"] == 0.0


def test_cache_hit_share_computed_from_trace_steps():
    hit = _at(_trace(feature=Trace.Feature.DIGEST), _mid_this_month())
    TraceStep.objects.create(trace=hit, seq=0, kind=TraceStep.Kind.LLM, detail={"cache": "exact"})
    _at(_trace(feature=Trace.Feature.DIGEST), _mid_this_month())  # a miss, no cache step

    resp = _admin().get(USAGE_URL)
    assert resp.json()["data"]["totals"]["cache_hit_share"] == pytest.approx(0.5)


# --- degraded minutes -------------------------------------------------------------------------

def test_degraded_minutes_counts_distinct_minutes_with_skipped_routing():
    when = _mid_this_month()
    _at(_trace(meta={"routing": {"chain": ["anthropic", "gemini"], "chosen": "gemini",
                                 "skipped": ["anthropic"]}}), when)
    # A second call in the very same minute with the same evidence must not double-count.
    _at(_trace(meta={"routing": {"chain": ["anthropic", "gemini"], "chosen": "gemini",
                                 "skipped": ["anthropic"]}}), when)
    # A clean call (no skipped provider) contributes nothing.
    _at(_trace(meta={"routing": {"chain": ["anthropic"], "chosen": "anthropic", "skipped": []}}),
        when)

    resp = _admin().get(USAGE_URL)
    assert resp.json()["data"]["totals"]["degraded_minutes"] == 1


def test_degraded_minutes_zero_when_no_routing_evidence():
    _at(_trace(), _mid_this_month())
    resp = _admin().get(USAGE_URL)
    assert resp.json()["data"]["totals"]["degraded_minutes"] == 0


# --- budget vs consumed -----------------------------------------------------------------------

def test_budget_vs_consumed_org_scope_reads_the_queried_months_rollup():
    Budget.objects.filter(scope=Budget.Scope.ORG).update(limit_microcents=1_000)
    SpendRollup.objects.create(scope=Budget.Scope.ORG, scope_key="org",
                               period=_this_month_start(), spend_microcents=250)

    resp = _admin().get(USAGE_URL)
    org = resp.json()["data"]["budget"]["org"]
    assert org["limit_microcents"] == 1_000
    assert org["consumed_microcents"] == 250


def test_budget_vs_consumed_org_scope_zero_when_no_rollup_yet():
    resp = _admin().get(USAGE_URL)
    assert resp.json()["data"]["budget"]["org"]["consumed_microcents"] == 0


def test_budget_request_and_user_daily_expose_config_only():
    Budget.objects.filter(scope=Budget.Scope.REQUEST).update(limit_microcents=5, action=Budget.Action.BLOCK)
    Budget.objects.filter(scope=Budget.Scope.USER).update(limit_microcents=50, action=Budget.Action.NOTIFY)

    resp = _admin().get(USAGE_URL)
    budget = resp.json()["data"]["budget"]
    assert budget["request"] == {"limit_microcents": 5, "action": "block"}
    assert budget["user_daily"] == {"limit_microcents": 50, "action": "notify"}
