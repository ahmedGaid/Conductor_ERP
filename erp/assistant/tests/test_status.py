"""Degraded mode + status surface (ai-reliability T2.9): ``/api/assistant/status`` tells the
truth about AI health — ``full`` when every provider is closed and no budget is exhausted,
``degraded`` while a fallback chain or a blocked budget is in play but a usable provider
remains, ``down`` only when every provider is breaker-open."""
from __future__ import annotations

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from erp.assistant.gateway import breaker, status
from erp.assistant.models import Budget, SpendRollup
from erp.identity.models import User

pytestmark = pytest.mark.django_db

PROVIDER_SETTINGS = dict(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="",
                         MISTRAL_API_KEY="", ASSISTANT_PROVIDER="")
WIDE_OPEN = 10_000_000_000  # a limit no test call could realistically reach


def _user(username: str) -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


@pytest.fixture(autouse=True)
def _wide_open_budgets():
    Budget.objects.filter(scope=Budget.Scope.REQUEST).update(
        limit_microcents=WIDE_OPEN, action=Budget.Action.BLOCK)
    Budget.objects.filter(scope=Budget.Scope.USER).update(
        limit_microcents=WIDE_OPEN, action=Budget.Action.BLOCK)
    Budget.objects.filter(scope=Budget.Scope.ORG).update(
        limit_microcents=WIDE_OPEN, action=Budget.Action.BLOCK)
    yield


@override_settings(**PROVIDER_SETTINGS)
def test_full_when_all_closed_and_under_budget():
    assert status.mode() == "full"


@override_settings(**PROVIDER_SETTINGS)
def test_degraded_when_one_provider_open_but_another_usable():
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("anthropic")
    assert status.mode() == "degraded"


@override_settings(**PROVIDER_SETTINGS)
def test_down_when_every_provider_is_open():
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("anthropic")
        breaker.record_failure("gemini")
    assert status.mode() == "down"


@override_settings(**PROVIDER_SETTINGS)
def test_degraded_when_org_budget_block_exhausted():
    Budget.objects.filter(scope=Budget.Scope.ORG).update(limit_microcents=100)
    SpendRollup.objects.create(scope=Budget.Scope.ORG, scope_key="org",
                               period=timezone.now().date().replace(day=1), spend_microcents=100)
    assert status.mode() == "degraded"


@override_settings(**PROVIDER_SETTINGS)
def test_notify_mode_budget_over_limit_does_not_degrade():
    # notify-mode never blocks a call, so it shouldn't read as degraded either.
    Budget.objects.filter(scope=Budget.Scope.ORG).update(
        limit_microcents=100, action=Budget.Action.NOTIFY)
    SpendRollup.objects.create(scope=Budget.Scope.ORG, scope_key="org",
                               period=timezone.now().date().replace(day=1), spend_microcents=100)
    assert status.mode() == "full"


@override_settings(**PROVIDER_SETTINGS, ASSISTANT_ENABLED=True)
def test_status_endpoint_reports_mode():
    client = APIClient()
    client.force_authenticate(_user("status_view"))
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("anthropic")

    resp = client.get("/api/assistant/status")

    assert resp.status_code == 200
    assert resp.data["data"]["enabled"] is True
    assert resp.data["data"]["mode"] == "degraded"


@override_settings(ASSISTANT_ENABLED=False)
def test_status_endpoint_reports_full_when_disabled():
    client = APIClient()
    client.force_authenticate(_user("status_view_disabled"))

    resp = client.get("/api/assistant/status")

    assert resp.data["data"]["enabled"] is False
    assert resp.data["data"]["mode"] == "full"
