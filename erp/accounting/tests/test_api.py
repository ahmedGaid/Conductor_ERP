"""Accounting DRF API — accounts, journals, posting, reports, period lock, RBAC."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="acct_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _bootstrap(client) -> None:
    for code, name, type_, postable in [
        ("1000", "Cash", "asset", True),
        ("3000", "Capital", "equity", True),
        ("4000", "Sales", "income", True),
        ("1100", "AR", "asset", True),
    ]:
        res = client.post(
            "/api/accounting/accounts",
            {"code": code, "name": name, "type": type_, "is_postable": postable},
            format="json",
        )
        assert res.status_code == 201, res.data
    assert client.post(
        "/api/accounting/fiscal-years",
        {"code": "2026", "start_date": "2026-01-01", "end_date": "2026-12-31"},
        format="json",
    ).status_code == 201
    assert client.post(
        "/api/accounting/periods",
        {
            "fiscal_year_code": "2026",
            "code": "2026-06",
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
        },
        format="json",
    ).status_code == 201


def _post_journal(client, lines, date="2026-06-15"):
    return client.post(
        "/api/accounting/journals",
        {"date": date, "memo": "test", "lines": lines},
        format="json",
    )


def test_post_journal_and_trial_balance_via_api():
    client = _admin_client()
    _bootstrap(client)

    res = _post_journal(
        client,
        [
            {"account_code": "1000", "debit": 100_00, "credit": 0},
            {"account_code": "3000", "debit": 0, "credit": 100_00},
        ],
    )
    assert res.status_code == 201, res.data
    assert res.data["data"]["status"] == "posted"
    assert len(res.data["data"]["lines"]) == 2

    tb = client.get("/api/accounting/reports/trial-balance").data["data"]
    assert tb["is_balanced"] is True
    assert tb["total_debit"] == tb["total_credit"] == 100_00


def test_unbalanced_journal_rejected_via_api():
    client = _admin_client()
    _bootstrap(client)
    res = _post_journal(
        client,
        [
            {"account_code": "1000", "debit": 100_00, "credit": 0},
            {"account_code": "3000", "debit": 0, "credit": 90_00},
        ],
    )
    assert res.status_code == 422
    assert res.data["error"]["code"] == "ACC-001"
    assert client.get("/api/accounting/journals").data["data"] == []


def test_general_ledger_via_api():
    client = _admin_client()
    _bootstrap(client)
    _post_journal(
        client,
        [
            {"account_code": "1100", "debit": 300_00, "credit": 0},
            {"account_code": "4000", "debit": 0, "credit": 300_00},
        ],
    )
    gl = client.get("/api/accounting/reports/general-ledger?account=1100").data["data"]
    assert gl["closing_balance"] == 300_00
    assert len(gl["lines"]) == 1


def test_closed_period_blocks_posting_via_api():
    client = _admin_client()
    _bootstrap(client)
    assert client.post("/api/accounting/periods/2026-06/close").status_code == 200
    res = _post_journal(
        client,
        [
            {"account_code": "1000", "debit": 10_00, "credit": 0},
            {"account_code": "3000", "debit": 0, "credit": 10_00},
        ],
    )
    assert res.status_code == 422
    assert res.data["error"]["code"] == "ACC-003"


def test_accounting_requires_role():
    plain = User.objects.create_user(username="nobody", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    assert client.get("/api/accounting/accounts").status_code == 403


def test_requires_authentication():
    assert APIClient().get("/api/accounting/accounts").status_code == 401
