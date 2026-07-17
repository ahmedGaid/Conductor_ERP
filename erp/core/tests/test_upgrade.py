"""manage.py upgrade: applies pending registry steps once, records them, halts cleanly on a
mid-run failure without repeating completed steps (twenty-harvest FILE_02)."""
from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from erp.core import upgrades
from erp.core.models import AppliedUpgradeStep
from erp.core.upgrades import UpgradeStep


def _run(**opts):
    call_command("upgrade", "--yes", "--skip-backup-check", verbosity=0, **opts)


@pytest.fixture
def two_step_registry(monkeypatch):
    calls: list[str] = []
    steps = [
        UpgradeStep(version="1.1.0", name="step_one", run=lambda: calls.append("one")),
        UpgradeStep(version="1.1.0", name="step_two", run=lambda: calls.append("two")),
    ]
    monkeypatch.setattr(upgrades, "REGISTRY", steps)
    return calls


def test_fresh_run_applies_all_steps_and_records_them(db, two_step_registry):
    _run()

    assert two_step_registry == ["one", "two"]
    assert set(AppliedUpgradeStep.objects.values_list("version", "name")) == {
        ("1.1.0", "step_one"),
        ("1.1.0", "step_two"),
    }


def test_second_run_is_a_clean_noop(db, two_step_registry):
    _run()
    two_step_registry.clear()

    _run()

    assert two_step_registry == []
    assert AppliedUpgradeStep.objects.count() == 2


def test_mid_run_failure_halts_without_repeating_completed_steps(db, monkeypatch):
    calls: list[str] = []

    def _boom():
        raise RuntimeError("boom")

    steps = [
        UpgradeStep(version="1.1.0", name="step_one", run=lambda: calls.append("one")),
        UpgradeStep(version="1.1.0", name="step_two", run=_boom),
        UpgradeStep(version="1.1.0", name="step_three", run=lambda: calls.append("three")),
    ]
    monkeypatch.setattr(upgrades, "REGISTRY", steps)

    with pytest.raises(CommandError, match="step_two"):
        _run()

    assert calls == ["one"]
    assert list(AppliedUpgradeStep.objects.values_list("version", "name")) == [
        ("1.1.0", "step_one")
    ]

    # Fix the cause and re-run: step_one is not repeated, step_two/step_three run once.
    steps[1] = UpgradeStep(version="1.1.0", name="step_two", run=lambda: calls.append("two"))
    monkeypatch.setattr(upgrades, "REGISTRY", steps)

    _run()

    assert calls == ["one", "two", "three"]
    assert AppliedUpgradeStep.objects.count() == 3


def test_prints_version_and_ok_when_no_pending_steps(db, monkeypatch, capsys):
    monkeypatch.setattr(upgrades, "REGISTRY", [])

    _run()

    out = capsys.readouterr().out
    assert "No pending steps" in out
    assert "OK" in out
