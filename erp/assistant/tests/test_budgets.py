"""Token & cost budgets (ai-reliability T2.7): a block-mode scope stops a call before any
provider is tried; a notify-mode scope only logs; spend rolls up atomically and resets correctly
at a day/month boundary; the ops summary shows spend vs budget per scope."""
from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from erp.assistant.errors import BudgetExceeded
from erp.assistant.gateway import budgets
from erp.assistant.gateway import core as llm
from erp.assistant.models import Budget, SpendRollup, Trace
from erp.identity.models import User

pytestmark = pytest.mark.django_db

PROVIDER_SETTINGS = dict(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="",
                         MISTRAL_API_KEY="", ASSISTANT_PROVIDER="")

WIDE_OPEN = 10_000_000_000  # a limit no test call could realistically reach


def _user(username: str) -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


def _counting_runner(monkeypatch, response: str = '{"ok": true}') -> dict:
    calls = {"n": 0}

    def runner(*_a, **_k):
        calls["n"] += 1
        return response

    monkeypatch.setitem(llm._RUNNERS, "anthropic", runner)
    return calls


@pytest.fixture(autouse=True)
def _wide_open_budgets():
    # Migration 0007 seeds all three scopes; start every test from a limit no call could hit, so
    # each test only has to narrow the one scope it's actually exercising.
    Budget.objects.filter(scope=Budget.Scope.REQUEST).update(
        limit_microcents=WIDE_OPEN, action=Budget.Action.BLOCK)
    Budget.objects.filter(scope=Budget.Scope.USER).update(
        limit_microcents=WIDE_OPEN, action=Budget.Action.BLOCK)
    Budget.objects.filter(scope=Budget.Scope.ORG).update(
        limit_microcents=WIDE_OPEN, action=Budget.Action.BLOCK)
    yield


# --- request scope: pre-call estimate, no rollup involved -----------------------------------------

@override_settings(**PROVIDER_SETTINGS)
def test_request_over_cap_blocked_pre_call(monkeypatch):
    calls = _counting_runner(monkeypatch)
    Budget.objects.filter(scope=Budget.Scope.REQUEST).update(limit_microcents=1)
    actor = _user("req_block")

    with pytest.raises(BudgetExceeded):
        llm.complete_json("sys", "user", {}, feature="ask", actor=actor)

    assert calls["n"] == 0  # blocked before any provider was tried
    trace = Trace.objects.get()
    assert trace.status == Trace.Status.ERROR
    assert trace.error_class == "budget_exceeded"


@override_settings(**PROVIDER_SETTINGS)
def test_request_under_cap_allowed(monkeypatch):
    calls = _counting_runner(monkeypatch)
    result = llm.complete_json("sys", "user", {}, feature="ask", actor=_user("req_ok"))
    assert result == {"ok": True}
    assert calls["n"] == 1


@override_settings(**PROVIDER_SETTINGS)
def test_stream_blocked_pre_call(monkeypatch):
    def runner(*_a, **_k):
        raise AssertionError("provider must never be called when budget-blocked")

    monkeypatch.setitem(llm._STREAM_RUNNERS, "anthropic", runner)
    Budget.objects.filter(scope=Budget.Scope.REQUEST).update(limit_microcents=1)

    with pytest.raises(BudgetExceeded):
        list(llm.complete_stream([{"role": "user", "content": "hi"}], feature="chat",
                                 actor=_user("stream_block")))


# --- user/day scope ---------------------------------------------------------------------------------

@override_settings(**PROVIDER_SETTINGS)
def test_user_day_exhausted_blocks(monkeypatch):
    calls = _counting_runner(monkeypatch)
    Budget.objects.filter(scope=Budget.Scope.USER).update(limit_microcents=100)
    actor = _user("user_block")
    SpendRollup.objects.create(scope=Budget.Scope.USER, scope_key=str(actor.id),
                               period=timezone.now().date(), spend_microcents=100)

    with pytest.raises(BudgetExceeded):
        llm.complete_json("sys", "user", {}, feature="ask", actor=actor)
    assert calls["n"] == 0


@override_settings(**PROVIDER_SETTINGS)
def test_user_day_scope_is_per_user(monkeypatch):
    calls = _counting_runner(monkeypatch)
    # High enough that one fresh call fits, but a user already sitting at the limit doesn't.
    Budget.objects.filter(scope=Budget.Scope.USER).update(limit_microcents=100_000)
    spent_user = _user("user_spent")
    fresh_user = _user("user_fresh")
    SpendRollup.objects.create(scope=Budget.Scope.USER, scope_key=str(spent_user.id),
                               period=timezone.now().date(), spend_microcents=100_000)

    result = llm.complete_json("sys", "user", {}, feature="ask", actor=fresh_user)
    assert result == {"ok": True}
    assert calls["n"] == 1


# --- org/month scope ---------------------------------------------------------------------------------

@override_settings(**PROVIDER_SETTINGS)
def test_org_month_exhausted_blocks(monkeypatch):
    calls = _counting_runner(monkeypatch)
    Budget.objects.filter(scope=Budget.Scope.ORG).update(limit_microcents=100)
    SpendRollup.objects.create(scope=Budget.Scope.ORG, scope_key=budgets.ORG_KEY,
                               period=timezone.now().date().replace(day=1), spend_microcents=100)

    with pytest.raises(BudgetExceeded):
        llm.complete_json("sys", "user", {}, feature="ask", actor=_user("org_block"))
    assert calls["n"] == 0


# --- notify mode: logs, never blocks -----------------------------------------------------------------

@override_settings(**PROVIDER_SETTINGS)
def test_notify_mode_logs_but_allows(monkeypatch, caplog):
    calls = _counting_runner(monkeypatch)
    Budget.objects.filter(scope=Budget.Scope.USER).update(
        limit_microcents=1, action=Budget.Action.NOTIFY)

    with caplog.at_level(logging.WARNING, logger="erp.assistant.gateway.budgets"):
        result = llm.complete_json("sys", "user", {}, feature="ask", actor=_user("user_notify"))

    assert result == {"ok": True}
    assert calls["n"] == 1
    assert any("notify mode" in r.message for r in caplog.records)


# --- rollup: atomic increment, correct across a day/month boundary -----------------------------------

def test_record_spend_increments_atomically():
    actor = _user("rollup_user")
    budgets.record_spend(actor=actor, cost_microcents=50)
    budgets.record_spend(actor=actor, cost_microcents=30)

    row = SpendRollup.objects.get(scope=Budget.Scope.USER, scope_key=str(actor.id))
    assert row.spend_microcents == 80


def test_user_rollup_resets_across_day_boundary():
    actor = _user("rollup_day")
    yesterday = timezone.now().date() - timedelta(days=1)
    SpendRollup.objects.create(scope=Budget.Scope.USER, scope_key=str(actor.id),
                               period=yesterday, spend_microcents=999)

    budgets.record_spend(actor=actor, cost_microcents=10)

    today_row = SpendRollup.objects.get(scope=Budget.Scope.USER, scope_key=str(actor.id),
                                        period=timezone.now().date())
    assert today_row.spend_microcents == 10  # yesterday's spend never counted toward today
    yesterday_row = SpendRollup.objects.get(scope=Budget.Scope.USER, scope_key=str(actor.id),
                                            period=yesterday)
    assert yesterday_row.spend_microcents == 999  # untouched


def test_org_rollup_accumulates_within_month_and_resets_next_month():
    first_of_month = timezone.now().date().replace(day=1)
    prev_month = (first_of_month - timedelta(days=1)).replace(day=1)
    SpendRollup.objects.create(scope=Budget.Scope.ORG, scope_key=budgets.ORG_KEY,
                               period=prev_month, spend_microcents=500)

    budgets.record_spend(actor=None, cost_microcents=20)
    budgets.record_spend(actor=None, cost_microcents=30)

    this_month = SpendRollup.objects.get(scope=Budget.Scope.ORG, scope_key=budgets.ORG_KEY,
                                         period=first_of_month)
    assert this_month.spend_microcents == 50  # two same-month calls accumulate on one row
    prev_row = SpendRollup.objects.get(scope=Budget.Scope.ORG, scope_key=budgets.ORG_KEY,
                                       period=prev_month)
    assert prev_row.spend_microcents == 500  # last month's row is untouched


# --- ops visibility -------------------------------------------------------------------------------

@override_settings(**PROVIDER_SETTINGS)
def test_ops_summary_shows_spend_vs_budget_per_scope(monkeypatch):
    _counting_runner(monkeypatch)
    llm.complete_json("sys", "user", {}, feature="ask", actor=_user("ops_budget"))

    admin = User.objects.create_user(username="ops_budget_admin", password="Dev12345!",
                                     email="ops_budget_admin@example.test", is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=admin)
    data = client.get("/api/assistant/ops/summary").json()["data"]

    by_scope = {b["scope"]: b for b in data["budgets"]}
    assert set(by_scope) == {"request", "user", "org"}
    assert by_scope["request"]["spend_microcents"] is None  # nothing rolled up for this scope
    assert by_scope["user"]["spend_microcents"] > 0
    assert by_scope["org"]["spend_microcents"] > 0
