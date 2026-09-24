"""provision_customer: refuses a dirty DB, rejects weak/known admin passwords, and --verify
catches a leftover user on an otherwise-clean install (delivery-readiness FILE_06)."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from erp.pricing.domain.models import PriceList

User = get_user_model()

STRONG_PASSWORD = "Correct-Horse-Battery-99"
ENV_VAR = "TEST_PROVISION_ADMIN_PASSWORD"


def _provision(monkeypatch, password: str) -> None:
    monkeypatch.setenv(ENV_VAR, password)
    call_command("provision_customer", "--admin-password-env", ENV_VAR, verbosity=0)


def test_refuses_a_dirty_database(db, monkeypatch):
    User.objects.create_user(username="someone")

    with pytest.raises(CommandError, match="not empty"):
        _provision(monkeypatch, STRONG_PASSWORD)


def test_refuses_the_known_dev_password(db, monkeypatch):
    with pytest.raises(CommandError, match="rejected"):
        _provision(monkeypatch, "Dev12345!")


def test_refuses_a_short_password(db, monkeypatch):
    with pytest.raises(CommandError, match="rejected"):
        _provision(monkeypatch, "Sh0rt!")


def test_happy_path_provisions_an_admin_only_tenant(db, monkeypatch):
    _provision(monkeypatch, STRONG_PASSWORD)

    admin = User.objects.get(username="admin")
    assert admin.check_password(STRONG_PASSWORD)
    assert User.objects.count() == 1
    assert PriceList.objects.filter(is_default=True, is_active=True).count() == 1

    # --verify passes against the install it just produced.
    call_command("provision_customer", "--verify", verbosity=0)


def test_verify_catches_a_planted_extra_user(db, monkeypatch):
    _provision(monkeypatch, STRONG_PASSWORD)
    User.objects.create_user(username="phase1d_qa")

    with pytest.raises(CommandError, match="verification failed"):
        call_command("provision_customer", "--verify", verbosity=0)


def test_go_live_without_license_file_runs_as_trial(db, monkeypatch, settings, capsys):
    settings.LICENSE_MODE = "enforce"
    _provision(monkeypatch, STRONG_PASSWORD)
    call_command("provision_customer", "--verify", verbosity=0)
    assert "trial" in capsys.readouterr().out


def test_go_live_with_license_file_installs_it(db, monkeypatch, settings, tmp_path, capsys):
    import datetime as dt

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from erp.licensing import core, verify as verify_mod
    from erp.licensing.core import EDITIONS
    from erp.licensing.state import get_installed

    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(verify_mod, "configured_public_keys", lambda: [private_key.public_key()])
    settings.LICENSE_MODE = "enforce"

    info = core.LicenseInfo(
        license_id="LIC-GOLIVE",
        company_name="Go Live Co",
        tax_id="123456789",
        edition="basic",
        modules=tuple(EDITIONS["basic"]["modules"]),
        max_branches=1,
        issued_at=dt.date(2026, 1, 1),
        maintenance_until=dt.date(2099, 1, 1),
        ai_until=None,
    )
    key = core.sign(info, private_key)
    lic_path = tmp_path / "customer.lic"
    lic_path.write_text(key, encoding="utf-8")

    monkeypatch.setenv(ENV_VAR, STRONG_PASSWORD)
    call_command(
        "provision_customer", "--admin-password-env", ENV_VAR,
        "--license-file", str(lic_path), verbosity=0,
    )
    # Go-live doesn't set the org's VAT number, so the report shows company_mismatch — the key
    # itself is installed regardless (cryptographic verify only; the report doesn't gate on it).
    assert get_installed().key_text == key
    assert "license:" in capsys.readouterr().out


def test_go_live_with_invalid_license_file_fails(db, monkeypatch, settings, tmp_path):
    settings.LICENSE_MODE = "enforce"
    lic_path = tmp_path / "bad.lic"
    lic_path.write_text("not-a-real-key", encoding="utf-8")

    monkeypatch.setenv(ENV_VAR, STRONG_PASSWORD)
    with pytest.raises(CommandError, match="rejected"):
        call_command(
            "provision_customer", "--admin-password-env", ENV_VAR,
            "--license-file", str(lic_path), verbosity=0,
        )
