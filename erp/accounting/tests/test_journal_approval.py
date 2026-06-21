"""Manual journal approval limits — a large manual journal may be posted only by an actor whose
'journal' approval limit covers it (Increment 6 limits, now wired into the manual GL post). Module/
system posts and superuser/System Admin are unrestricted. Runs under gate05 (erp/accounting/tests).
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.accounting import services
from erp.accounting.errors import ApprovalLimitExceededError
from erp.identity.models import ApprovalLimit, User
from erp.identity.roles import ACCOUNTANT

from .test_api import _bootstrap

pytestmark = pytest.mark.django_db

THRESHOLD = services.JOURNAL_APPROVAL_THRESHOLD_MINOR  # 1,000,000 (10,000.00 EGP)


def _accountant(limit_minor) -> User:
    """An Accountant-role user carrying a 'journal' approval ceiling (None = unlimited)."""
    g, _ = Group.objects.get_or_create(name=ACCOUNTANT)
    ApprovalLimit.objects.update_or_create(
        role=g, document_type="journal", defaults={"limit_minor": limit_minor}
    )
    u = User.objects.create_user(username=f"acct{limit_minor}", email=f"a{limit_minor}@erp.local", password="pw12345!")
    u.groups.add(g)
    return u


# --- Service layer ---

def test_at_or_below_threshold_needs_no_approval():
    u = _accountant(0)  # zero ceiling, but small journals don't need approval
    services.enforce_journal_approval(u, THRESHOLD)       # exactly at threshold, not above
    services.enforce_journal_approval(u, THRESHOLD - 1)


def test_above_threshold_within_limit_ok():
    u = _accountant(3_000_000)
    services.enforce_journal_approval(u, 2_500_000)


def test_above_threshold_over_limit_rejected():
    u = _accountant(2_000_000)
    with pytest.raises(ApprovalLimitExceededError):
        services.enforce_journal_approval(u, 2_500_000)


def test_zero_ceiling_blocks_large_journal():
    u = _accountant(0)
    with pytest.raises(ApprovalLimitExceededError):
        services.enforce_journal_approval(u, 2_000_000)


def test_unlimited_passes():
    u = _accountant(None)
    services.enforce_journal_approval(u, 9_999_999)


def test_no_actor_and_superuser_unrestricted():
    services.enforce_journal_approval(None, 9_999_999)  # module / system post
    su = User.objects.create_user(username="root", email="root@erp.local", password="pw")
    su.is_superuser = True
    su.save(update_fields=["is_superuser"])
    services.enforce_journal_approval(su, 9_999_999)


# --- API (the manual journal post enforces it; module posts never hit this path) ---

def _su_client() -> APIClient:
    u = User.objects.create_user(username="root_api", email="root_api@erp.local", password="pw")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def _post(client, amount):
    return client.post(
        "/api/accounting/journals",
        {"date": "2026-06-15", "memo": "m",
         "lines": [{"account_code": "1100", "debit": amount, "credit": 0},
                   {"account_code": "4000", "debit": 0, "credit": amount}]},
        format="json",
    )


def test_api_large_manual_journal_blocked_then_small_allowed():
    _bootstrap(_su_client())  # accounts + period exist
    capped = _accountant(2_000_000)
    c = APIClient()
    c.force_authenticate(user=capped)

    over = _post(c, 2_500_000)
    assert over.status_code == 403
    assert over.data["error"]["code"] == "ACC-014"

    assert _post(c, 500_000).status_code == 201  # below threshold, fine


def test_api_unlimited_accountant_posts_large_journal():
    _bootstrap(_su_client())
    c = APIClient()
    c.force_authenticate(user=_accountant(None))
    assert _post(c, 5_000_000).status_code == 201
