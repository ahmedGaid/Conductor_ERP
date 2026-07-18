"""arp-roadmap track P item 2 — calm milestone moments: fires once, company-wide dismissal,
never nags, at most one shown at a time.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.monitoring import milestones
from erp.monitoring.models import MilestoneAck

pytestmark = pytest.mark.django_db

MILESTONES_URL = "/api/dashboard/milestones/"


@pytest.fixture
def user_client() -> APIClient:
    user = User.objects.create_user(username="ms_plain", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_anonymous_is_401_or_403():
    assert APIClient().get(MILESTONES_URL).status_code in (401, 403)


def test_no_milestone_pending_by_default(user_client):
    resp = user_client.get(MILESTONES_URL)
    assert resp.status_code == 200
    assert resp.json()["data"]["milestone"] is None


def test_invoice_count_milestone_fires_once_crossed(user_client, monkeypatch):
    monkeypatch.setattr(milestones, "invoiced_order_count", lambda: 150)
    resp = user_client.get(MILESTONES_URL)
    milestone = resp.json()["data"]["milestone"]
    assert milestone == {"key": "invoices_100", "kind": "invoice_count", "value": 100}


def test_invoice_count_milestone_picks_highest_threshold(user_client, monkeypatch):
    monkeypatch.setattr(milestones, "invoiced_order_count", lambda: 1_200)
    resp = user_client.get(MILESTONES_URL)
    assert resp.json()["data"]["milestone"]["key"] == "invoices_1000"


def test_dismiss_is_idempotent_and_company_wide(user_client, monkeypatch):
    monkeypatch.setattr(milestones, "invoiced_order_count", lambda: 150)
    assert user_client.get(MILESTONES_URL).json()["data"]["milestone"]["key"] == "invoices_100"

    resp = user_client.post("/api/dashboard/milestones/invoices_100/dismiss/")
    assert resp.status_code == 200
    assert MilestoneAck.objects.filter(key="invoices_100").count() == 1

    # dismissing again must not error or duplicate
    user_client.post("/api/dashboard/milestones/invoices_100/dismiss/")
    assert MilestoneAck.objects.filter(key="invoices_100").count() == 1

    # gone for everyone now — a second user sees nothing pending
    other = User.objects.create_user(username="ms_other", password="Dev12345!", email="ms_other@example.com")
    other_client = APIClient()
    other_client.force_authenticate(user=other)
    assert other_client.get(MILESTONES_URL).json()["data"]["milestone"] is None


def test_first_profitable_month_milestone(user_client, monkeypatch):
    monkeypatch.setattr(milestones, "invoiced_order_count", lambda: 0)
    monkeypatch.setattr(
        milestones,
        "income_statement_summary",
        lambda period="this_month": {"net_income_minor": 5_000},
    )
    resp = user_client.get(MILESTONES_URL)
    assert resp.json()["data"]["milestone"] == {
        "key": "first_profitable_month", "kind": "first_profitable_month", "value": None,
    }


def test_at_most_one_milestone_shown_at_a_time(user_client, monkeypatch):
    monkeypatch.setattr(milestones, "invoiced_order_count", lambda: 150)
    monkeypatch.setattr(
        milestones,
        "income_statement_summary",
        lambda period="this_month": {"net_income_minor": 5_000},
    )
    milestone = user_client.get(MILESTONES_URL).json()["data"]["milestone"]
    assert milestone["key"] == "invoices_100"  # invoice-count checked first, only one surfaces
