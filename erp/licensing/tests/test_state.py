"""current_state() — every reachable state, plus trial day-boundary math (license-key FILE_02)."""
from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from erp.identity.services import get_org_preferences
from erp.licensing import core, state
from erp.licensing.core import EDITIONS

pytestmark = pytest.mark.django_db


@pytest.fixture
def private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


@pytest.fixture
def issue_key(private_key, monkeypatch):
    """Sign a key with the throwaway keypair, and make the app verifier trust it."""
    from erp.licensing import verify as verify_mod

    monkeypatch.setattr(verify_mod, "configured_public_keys", lambda: [private_key.public_key()])

    def _issue(**overrides) -> str:
        info = core.LicenseInfo(
            license_id="LIC-0001",
            company_name="Test Co",
            tax_id=overrides.pop("tax_id", "123-456-789"),
            edition="integrated",
            modules=tuple(EDITIONS["integrated"]["modules"]),
            max_branches=5,
            issued_at=dt.date(2026, 1, 1),
            maintenance_until=overrides.pop("maintenance_until", dt.date(2099, 1, 1)),
            ai_until=overrides.pop("ai_until", None),
        )
        return core.sign(info, private_key)

    return _issue


def test_unmanaged_when_license_mode_off(settings, db):
    settings.LICENSE_MODE = "off"
    assert state.current_state().status == "unmanaged"


def test_fresh_install_with_no_key_starts_a_trial(settings, db):
    settings.LICENSE_MODE = "enforce"
    s = state.current_state()
    assert s.status == "trial"
    assert s.trial_days_left == state.TRIAL_DAYS


def test_trial_last_day_is_still_trial(settings, db):
    settings.LICENSE_MODE = "enforce"
    installed = state.get_installed()
    installed.first_run_at = timezone.now() - dt.timedelta(days=state.TRIAL_DAYS - 1)
    installed.save(update_fields=["first_run_at"])

    today = timezone.localtime(installed.first_run_at).date() + dt.timedelta(days=state.TRIAL_DAYS - 1)
    s = state.current_state(today=today)
    assert s.status == "trial"
    assert s.trial_days_left == 1


def test_trial_ends_the_day_after(settings, db):
    settings.LICENSE_MODE = "enforce"
    installed = state.get_installed()
    installed.first_run_at = timezone.now()
    installed.save(update_fields=["first_run_at"])

    trial_start = timezone.localtime(installed.first_run_at).date()
    s = state.current_state(today=trial_start + dt.timedelta(days=state.TRIAL_DAYS))
    assert s.status == "trial_ended"
    assert s.trial_days_left == 0


def test_active_when_key_installed_and_tax_id_matches(settings, db, issue_key):
    settings.LICENSE_MODE = "enforce"
    org = get_org_preferences()
    org.vat_number = "123-456-789"
    org.save(update_fields=["vat_number"])

    installed = state.get_installed()
    installed.key_text = issue_key(tax_id="123456789")
    installed.save(update_fields=["key_text"])

    s = state.current_state()
    assert s.status == "active"
    assert s.edition == "integrated"
    assert s.max_branches == 5
    assert s.maintenance_active is True


def test_company_mismatch_when_org_vat_changes(settings, db, issue_key):
    settings.LICENSE_MODE = "enforce"
    org = get_org_preferences()
    org.vat_number = "123-456-789"
    org.save(update_fields=["vat_number"])

    installed = state.get_installed()
    installed.key_text = issue_key(tax_id="123-456-789")
    installed.save(update_fields=["key_text"])
    assert state.current_state().status == "active"

    org.vat_number = "999-999-999"
    org.save(update_fields=["vat_number"])
    assert state.current_state().status == "company_mismatch"


def test_invalid_key_never_raises_no_public_key_configured(settings, db):
    # keys.PUBLIC_KEYS is empty in test settings, same as a real install before --new-keypair.
    settings.LICENSE_MODE = "enforce"
    installed = state.get_installed()
    installed.key_text = "not-a-real-key"
    installed.save(update_fields=["key_text"])

    s = state.current_state()
    assert s.status == "invalid"
    assert s.invalid_reason == "no_public_key"


def test_invalid_key_never_raises_malformed(settings, db, monkeypatch, private_key):
    from erp.licensing import verify as verify_mod

    monkeypatch.setattr(verify_mod, "configured_public_keys", lambda: [private_key.public_key()])
    settings.LICENSE_MODE = "enforce"
    installed = state.get_installed()
    installed.key_text = "not-a-real-key"
    installed.save(update_fields=["key_text"])

    s = state.current_state()
    assert s.status == "invalid"
    assert s.invalid_reason == "malformed"


def test_maintenance_and_ai_expiry_are_evaluated_against_today(settings, db, issue_key):
    settings.LICENSE_MODE = "enforce"
    org = get_org_preferences()
    org.vat_number = "123456789"
    org.save(update_fields=["vat_number"])

    installed = state.get_installed()
    installed.key_text = issue_key(
        tax_id="123456789",
        maintenance_until=dt.date(2026, 1, 1),
        ai_until=dt.date(2026, 1, 1),
    )
    installed.save(update_fields=["key_text"])

    s = state.current_state(today=dt.date(2026, 6, 1))
    assert s.status == "active"
    assert s.maintenance_active is False
    assert s.ai_active is False
