"""Data-scope enforcement — accounting transactional records.

post_journal stamps the actor's branch; the journals list + detail narrow a BRANCH-scoped user to
their own branch (plus unstamped/NULL records), and an out-of-scope journal 404s. Masters (accounts,
periods, tax codes, cost centers) stay org-wide reference data by design.
"""
from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.accounting.services import JournalInput, LineInput, post_journal
from erp.core.models import Branch
from erp.identity.models import RolePermission, User
from erp.identity.roles import BRANCH_MANAGER

from .factories import make_coa, make_period

pytestmark = pytest.mark.django_db

VIEW = "accounting.journal.view"
DATE = dt.date(2026, 6, 15)


def _manager(username: str, branch: Branch | None, scope: str = "branch") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    RolePermission.objects.update_or_create(role=bm, code=VIEW, defaults={"scope": scope})
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.branch = branch
    u.save(update_fields=["branch"])
    u.groups.add(bm)
    return u


def _journal(actor=None):
    return post_journal(
        JournalInput(date=DATE, memo="test", lines=[
            LineInput(account_code="1000", debit=100_00),
            LineInput(account_code="4000", credit=100_00),
        ]),
        actor=actor,
    )


def test_post_journal_stamps_actor_branch():
    make_coa()
    make_period()
    branch = Branch.objects.create(code="BR-A", name="Alpha")
    mgr = _manager("mgr_a", branch)
    entry = _journal(mgr)
    assert entry.branch_id == branch.id
    assert entry.created_by_id == mgr.id


def test_journal_list_and_detail_are_branch_scoped():
    make_coa()
    make_period()
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _manager("mgr_a", a)
    mgr_b = _manager("mgr_b", b)
    entry_a = _journal(mgr_a)
    entry_b = _journal(mgr_b)
    entry_null = _journal(None)  # unstamped (system) journal stays visible to every branch

    client = APIClient()
    client.force_authenticate(user=mgr_a)
    rows = client.get("/api/accounting/journals").data["data"]
    assert {r["number"] for r in rows} == {entry_a.number, entry_null.number}

    assert client.get(f"/api/accounting/journals/{entry_a.id}").status_code == 200
    # Out of scope reads as absent — 404, never 403 (existence must not leak).
    assert client.get(f"/api/accounting/journals/{entry_b.id}").status_code == 404
