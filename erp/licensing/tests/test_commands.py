"""``manage.py license install|status`` (license-key FILE_02)."""
from __future__ import annotations

import datetime as dt
import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from erp.licensing import core
from erp.licensing.core import EDITIONS
from erp.licensing.state import get_installed

pytestmark = pytest.mark.django_db


@pytest.fixture
def private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


@pytest.fixture
def signed_key(private_key, monkeypatch, tmp_path):
    from erp.licensing import verify as verify_mod

    monkeypatch.setattr(verify_mod, "configured_public_keys", lambda: [private_key.public_key()])
    info = core.LicenseInfo(
        license_id="LIC-CMD",
        company_name="Cmd Co",
        tax_id="111-222-333",
        edition="basic",
        modules=tuple(EDITIONS["basic"]["modules"]),
        max_branches=1,
        issued_at=dt.date(2026, 1, 1),
        maintenance_until=dt.date(2099, 1, 1),
        ai_until=None,
    )
    key = core.sign(info, private_key)
    path = tmp_path / "test.lic"
    path.write_text(key, encoding="utf-8")
    return key, path


def test_status_reports_trial_before_any_key(settings, db):
    settings.LICENSE_MODE = "enforce"
    out = io.StringIO()
    call_command("license", "status", stdout=out)
    assert "trial" in out.getvalue()


def test_install_from_file_then_status_is_active(settings, db, signed_key):
    from erp.identity.services import get_org_preferences

    settings.LICENSE_MODE = "enforce"
    org = get_org_preferences()
    org.vat_number = "111-222-333"
    org.save(update_fields=["vat_number"])

    key, path = signed_key
    out = io.StringIO()
    call_command("license", "install", str(path), stdout=out)
    assert "Installed" in out.getvalue()
    assert get_installed().key_text == key

    status_out = io.StringIO()
    call_command("license", "status", stdout=status_out)
    assert "basic" in status_out.getvalue()


def test_install_key_text_directly(settings, db, signed_key):
    settings.LICENSE_MODE = "enforce"
    key, _ = signed_key
    call_command("license", "install", key, stdout=io.StringIO())
    assert get_installed().key_text == key


def test_install_refuses_invalid_key_with_reason(settings, db):
    # No public key is configured in test settings (keys.PUBLIC_KEYS is empty for real installs
    # too, until the founder runs --new-keypair) — that itself is a typed rejection reason.
    settings.LICENSE_MODE = "enforce"
    with pytest.raises(CommandError, match="no_public_key"):
        call_command("license", "install", "garbage", stdout=io.StringIO())
    assert get_installed().key_text == ""
