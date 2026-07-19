"""Weekly AI ops report (ai-reliability T1.9): Trace aggregation, eval-delta comparison, and the
admin dispatch path — mirrors ``test_digest.py``'s shape for the daily digest.
"""
from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Group

from erp.assistant.models import Trace
from erp.assistant.services import ops_report
from erp.identity.models import User
from erp.identity.roles import SYSTEM_ADMIN

pytestmark = pytest.mark.django_db


def _trace(**kw) -> Trace:
    defaults = dict(
        feature=Trace.Feature.ASK, provider="anthropic", model="claude-opus-4-8",
        input_tokens=100, output_tokens=50, cost_microcents=1_000_000, status=Trace.Status.OK,
    )
    defaults.update(kw)
    return Trace.objects.create(**defaults)


# --- build_report ---------------------------------------------------------------------------------

def test_build_report_aggregates_volume_cost_and_error_mix():
    _trace()
    _trace(status=Trace.Status.ERROR, error_class="rate_limited")
    _trace(status=Trace.Status.ERROR, error_class="rate_limited")
    _trace(status=Trace.Status.ERROR, error_class="")  # blank -> bucketed as unknown, never crashes

    report = ops_report.build_report(days=7)

    assert report["total_calls"] == 4
    assert report["error_rate"] == pytest.approx(0.75)
    assert report["cost_microcents"] == 4_000_000
    assert {"error_class": "rate_limited", "count": 2} in report["error_mix"]
    assert {"error_class": "unknown", "count": 1} in report["error_mix"]


def test_build_report_ignores_traces_outside_the_window():
    old = _trace()
    Trace.objects.filter(pk=old.pk).update(
        created_at=ops_report.timezone.now() - ops_report.timedelta(days=30)
    )

    report = ops_report.build_report(days=7)

    assert report["total_calls"] == 0


# --- eval_delta ------------------------------------------------------------------------------------

def test_eval_delta_none_when_no_scoreboard_recorded(monkeypatch, tmp_path):
    monkeypatch.setattr(ops_report, "RESULTS_DIR", tmp_path / "results")
    assert ops_report.eval_delta() is None


def test_eval_delta_compares_latest_against_previous(monkeypatch, tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "2026-06-01.json").write_text(json.dumps({"pass_rate": 0.80}), encoding="utf-8")
    (results / "2026-06-08.json").write_text(json.dumps({"pass_rate": 0.90}), encoding="utf-8")
    monkeypatch.setattr(ops_report, "RESULTS_DIR", results)

    delta = ops_report.eval_delta()

    assert delta["date"] == "2026-06-08"
    assert delta["pass_rate"] == 0.90
    assert delta["previous_pass_rate"] == 0.80
    assert delta["delta"] == pytest.approx(0.10)


def test_eval_delta_single_run_has_no_previous(monkeypatch, tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "2026-06-08.json").write_text(json.dumps({"pass_rate": 0.90}), encoding="utf-8")
    monkeypatch.setattr(ops_report, "RESULTS_DIR", results)

    delta = ops_report.eval_delta()

    assert delta["previous_pass_rate"] is None
    assert delta["delta"] is None


# --- send_weekly_report ------------------------------------------------------------------------

def test_send_weekly_report_writes_file_and_notifies_admins_only(monkeypatch, tmp_path):
    monkeypatch.setattr(ops_report, "DOCS_OPS_DIR", tmp_path)
    monkeypatch.setattr(ops_report, "RESULTS_DIR", tmp_path / "results")
    _trace()
    _trace(status=Trace.Status.ERROR, error_class="timeout")

    User.objects.create_user(username="wr_admin", password="Dev12345!",
                             email="admin@example.test", is_superuser=True)
    group = Group.objects.create(name=SYSTEM_ADMIN)
    role_holder = User.objects.create_user(username="wr_role", password="Dev12345!", email="")
    role_holder.groups.add(group)
    User.objects.create_user(username="wr_plain", password="Dev12345!", email="plain@example.test")

    calls: list[dict] = []
    monkeypatch.setattr(ops_report, "dispatch", lambda **kw: calls.append(kw))

    path = ops_report.send_weekly_report(days=7)

    assert path.exists()
    assert path.name.startswith("ai-week-")
    body = path.read_text(encoding="utf-8")
    assert "timeout" in body

    recipients = {c["recipient"] for c in calls}
    # wr_admin: inapp (username) + email; wr_role: inapp only (no email); wr_plain excluded entirely.
    assert recipients == {"wr_admin", "admin@example.test", "wr_role"}
    assert len(calls) == 3
