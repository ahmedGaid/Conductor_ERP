"""Enforcement: module 403s, read-only writes, branch limit, AI gate, e-invoice company binding,
clock rollback (license-key FILE_03)."""
from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity.roles import SYSTEM_ADMIN
from erp.identity.services import get_org_preferences
from erp.licensing import core, state
from erp.licensing.core import EDITIONS
from erp.licensing.state import get_installed

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def admin_client():
    Group.objects.get_or_create(name=SYSTEM_ADMIN)
    u = User.objects.create_user(username="root", email="root@erp.local", password="pw12345!")
    u.groups.add(Group.objects.get(name=SYSTEM_ADMIN))
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def plain_client():
    u = User.objects.create_user(username="plain", email="plain@erp.local", password="pw12345!")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


@pytest.fixture
def install_basic_key(private_key, monkeypatch):
    """Installs a verifiable BASIC-edition key (accounting/inventory/sales/purchasing/einvoice/
    notifications/administration — no crm, no workflow) matched to the org's VAT number."""
    from erp.licensing import verify as verify_mod

    monkeypatch.setattr(verify_mod, "configured_public_keys", lambda: [private_key.public_key()])

    def _install(**overrides) -> None:
        org = get_org_preferences()
        org.vat_number = "123456789"
        org.save(update_fields=["vat_number"])
        info = core.LicenseInfo(
            license_id="LIC-ENF",
            company_name="Enforcement Co",
            tax_id=overrides.pop("tax_id", "123456789"),
            edition="basic",
            modules=tuple(EDITIONS["basic"]["modules"]),
            max_branches=overrides.pop("max_branches", 1),
            issued_at=dt.date(2026, 1, 1),
            maintenance_until=dt.date(2099, 1, 1),
            ai_until=overrides.pop("ai_until", None),
        )
        installed = get_installed()
        installed.key_text = core.sign(info, private_key)
        installed.save(update_fields=["key_text"])

    return _install


# --- module gating -------------------------------------------------------------------------------

def test_unlicensed_module_403_in_enforce(settings, admin_client, install_basic_key):
    settings.LICENSE_MODE = "enforce"
    install_basic_key()
    resp = admin_client.get("/api/crm/leads")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "GEN-005"


def test_licensed_module_reachable(settings, admin_client, install_basic_key):
    settings.LICENSE_MODE = "enforce"
    install_basic_key()
    resp = admin_client.get("/api/sales/customers")
    assert resp.status_code == 200


def test_module_gate_is_noop_with_license_mode_off(settings, admin_client):
    settings.LICENSE_MODE = "off"
    resp = admin_client.get("/api/crm/leads")
    assert resp.status_code == 200


def test_module_gate_does_not_apply_during_trial(settings, admin_client):
    settings.LICENSE_MODE = "enforce"
    # No key installed at all -> trial, full module access.
    resp = admin_client.get("/api/crm/leads")
    assert resp.status_code == 200


# --- read-only guard -------------------------------------------------------------------------------

def test_trial_ended_blocks_writes_but_allows_reads(settings, admin_client):
    settings.LICENSE_MODE = "enforce"
    installed = get_installed()
    from django.utils import timezone

    installed.first_run_at = timezone.now() - dt.timedelta(days=state.TRIAL_DAYS)
    installed.save(update_fields=["first_run_at"])

    assert admin_client.get("/api/sales/customers").status_code == 200
    resp = admin_client.post("/api/sales/customers", {"name": "X", "code": "CUST-X"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "GEN-006"


def test_read_only_still_allows_license_post_and_signin(settings, admin_client):
    settings.LICENSE_MODE = "enforce"
    installed = get_installed()
    from django.utils import timezone

    installed.first_run_at = timezone.now() - dt.timedelta(days=state.TRIAL_DAYS)
    installed.save(update_fields=["first_run_at"])

    # A bad key is still processed by the view (400), not blocked by the read-only gate (403).
    resp = admin_client.post("/api/license/", {"key": "garbage"})
    assert resp.status_code == 400

    login_resp = APIClient().post("/api/identity/login", {"username": "root", "password": "pw12345!"})
    assert login_resp.status_code != 403


def test_active_license_allows_writes(settings, admin_client, install_basic_key):
    settings.LICENSE_MODE = "enforce"
    install_basic_key()
    resp = admin_client.post("/api/sales/customers", {"name": "Y", "code": "CUST-Y"})
    assert resp.status_code in (200, 201)


def test_read_only_blocks_patch_and_delete_too(settings, admin_client):
    settings.LICENSE_MODE = "enforce"
    installed = get_installed()
    from django.utils import timezone

    installed.first_run_at = timezone.now() - dt.timedelta(days=state.TRIAL_DAYS)
    installed.save(update_fields=["first_run_at"])

    assert admin_client.patch("/api/core/branches/HQ", {"name": "X"}).status_code == 403
    assert admin_client.delete("/api/sales/customers/NOSUCH").status_code == 403


def test_invalid_key_blocks_writes(settings, admin_client):
    settings.LICENSE_MODE = "enforce"
    installed = get_installed()
    installed.key_text = "garbage-key"
    installed.save(update_fields=["key_text"])

    assert admin_client.get("/api/sales/customers").status_code == 200
    resp = admin_client.post("/api/sales/customers", {"name": "X", "code": "CUST-X"})
    assert resp.status_code == 403


def test_company_mismatch_blocks_writes(settings, admin_client, install_basic_key):
    settings.LICENSE_MODE = "enforce"
    install_basic_key()
    org = get_org_preferences()
    org.vat_number = "000000000"
    org.save(update_fields=["vat_number"])

    resp = admin_client.post("/api/sales/customers", {"name": "X", "code": "CUST-X"})
    assert resp.status_code == 403


def test_logout_and_token_refresh_reachable_when_read_only(settings, admin_client):
    settings.LICENSE_MODE = "enforce"
    installed = get_installed()
    from django.utils import timezone

    installed.first_run_at = timezone.now() - dt.timedelta(days=state.TRIAL_DAYS)
    installed.save(update_fields=["first_run_at"])

    assert admin_client.post("/api/identity/logout").status_code != 403
    assert admin_client.post("/api/identity/token/refresh").status_code != 403


def test_current_state_failure_fails_open(settings, admin_client, monkeypatch):
    settings.LICENSE_MODE = "enforce"

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("erp.licensing.state.current_state", _boom)
    resp = admin_client.post("/api/sales/customers", {"name": "X", "code": "CUST-X"})
    assert resp.status_code != 403


# --- branch limit ---------------------------------------------------------------------------------

def test_branch_creation_blocked_at_max_branches(settings, admin_client, install_basic_key):
    settings.LICENSE_MODE = "enforce"
    install_basic_key(max_branches=1)  # HQ branch (seeded by migrations/fixtures) already fills it
    from erp.core.models import Branch

    Branch.objects.all().delete()
    Branch.objects.create(code="HQ", name="Headquarters")

    resp = admin_client.post("/api/core/branches", {"code": "BR2", "name": "Second"})
    assert resp.status_code == 400
    assert Branch.objects.count() == 1


def test_branch_creation_allowed_under_the_limit(settings, admin_client, install_basic_key):
    settings.LICENSE_MODE = "enforce"
    install_basic_key(max_branches=2)
    from erp.core.models import Branch

    Branch.objects.all().delete()
    Branch.objects.create(code="HQ", name="Headquarters")

    resp = admin_client.post("/api/core/branches", {"code": "BR2", "name": "Second"})
    assert resp.status_code == 201
    assert Branch.objects.count() == 2


def test_branch_limit_is_noop_when_unlimited(settings, admin_client, install_basic_key):
    settings.LICENSE_MODE = "enforce"
    install_basic_key(max_branches=None)
    resp = admin_client.post("/api/core/branches", {"code": "BR9", "name": "Ninth"})
    assert resp.status_code == 201


# --- AI add-on -------------------------------------------------------------------------------------

def test_ai_disabled_when_addon_not_active(settings, install_basic_key):
    from erp.assistant import client

    settings.ASSISTANT_ENABLED = True
    settings.LICENSE_MODE = "enforce"
    install_basic_key(ai_until=dt.date(2020, 1, 1))  # expired
    assert client.enabled() is False


def test_ai_enabled_when_addon_active(settings, install_basic_key):
    from erp.assistant import client

    settings.ASSISTANT_ENABLED = True
    settings.LICENSE_MODE = "enforce"
    install_basic_key(ai_until=dt.date(2099, 1, 1))
    assert client.enabled() is True


def test_ai_full_use_during_trial(settings):
    from erp.assistant import client

    settings.ASSISTANT_ENABLED = True
    settings.LICENSE_MODE = "enforce"
    assert client.enabled() is True


def test_ai_off_when_flag_off_regardless_of_license(settings, install_basic_key):
    from erp.assistant import client

    settings.ASSISTANT_ENABLED = False
    settings.LICENSE_MODE = "enforce"
    install_basic_key(ai_until=dt.date(2099, 1, 1))
    assert client.enabled() is False


# --- company binding (e-invoice) --------------------------------------------------------------------

def test_einvoice_submit_refused_on_company_mismatch(settings, install_basic_key):
    from erp.einvoice.domain.models import ETAInvoice, ETAStatus
    from erp.einvoice.errors import LicenseCompanyMismatchError
    from erp.einvoice.services import submit_invoice

    settings.LICENSE_MODE = "enforce"
    install_basic_key()
    org = get_org_preferences()
    org.vat_number = "999999999"  # now diverges from the installed key's tax_id
    org.save(update_fields=["vat_number"])

    eta = ETAInvoice.objects.create(
        invoice_number="INV-MISMATCH", issue_date=dt.date(2026, 1, 1), status=ETAStatus.DRAFT,
    )
    with pytest.raises(LicenseCompanyMismatchError):
        submit_invoice(eta)


# --- clock rollback --------------------------------------------------------------------------------

def test_clock_rollback_detected_and_never_locks_alone(settings, db):
    settings.LICENSE_MODE = "enforce"
    installed = state.get_installed()
    installed.first_run_at = None
    installed.last_seen_date = dt.date(2026, 6, 10)
    installed.save(update_fields=["first_run_at", "last_seen_date"])

    s = state.current_state(today=dt.date(2026, 6, 1))  # 9 days back
    assert s.clock_rollback is True
    assert s.status == "trial"  # never locked on the rollback alone


def test_clock_rollback_not_flagged_within_grace(settings, db):
    settings.LICENSE_MODE = "enforce"
    installed = state.get_installed()
    installed.first_run_at = None
    installed.last_seen_date = dt.date(2026, 6, 10)
    installed.save(update_fields=["first_run_at", "last_seen_date"])

    s = state.current_state(today=dt.date(2026, 6, 9))  # 1 day back, within grace
    assert s.clock_rollback is False
