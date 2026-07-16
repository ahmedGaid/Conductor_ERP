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
