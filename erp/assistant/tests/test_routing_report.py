"""T2.4: the routing report's baseline side is fully offline (grades real ``ask`` cases against
real recordings, zero network); the promotion rule is a pure function tested against fabricated
scoreboards so it never needs a live call either. Marker ``evals`` — same offline discipline as
``test_evals_smoke.py``."""
from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command, CommandError

from erp.assistant import client as assistant_client
from erp.assistant.evals import routing_report

pytestmark = pytest.mark.evals


@pytest.mark.django_db
def test_offline_scoreboard_ask_is_graded_and_priced():
    board = routing_report.offline_scoreboard("ask")
    assert board["model"] == "anthropic:claude-opus-4-8"
    assert board["cases_graded"] > 0
    assert board["pass_rate"] is not None
    assert 0.0 <= board["pass_rate"] <= 1.0
    assert board["cost_unknown"] is False
    assert board["cost_microcents_per_case"] > 0


@pytest.mark.django_db
def test_offline_scoreboard_suggest_has_no_runner_reports_none_not_perfect():
    """``suggest`` has golden cases but no offline runner — pass_rate must be ``None``, not the
    misleading ``1.0`` an empty graded set would otherwise imply."""
    board = routing_report.offline_scoreboard("suggest")
    assert board["cases_total"] > 0
    assert board["cases_graded"] == 0
    assert board["pass_rate"] is None


def test_baseline_model_for_unknown_task_raises():
    with pytest.raises(ValueError):
        routing_report.baseline_model_for("not_a_task")


def test_promotion_verdict_none_without_a_scored_candidate():
    baseline = {"pass_rate": 0.9, "cost_unknown": False, "cost_microcents_per_case": 100.0}
    assert routing_report.promotion_verdict(baseline, None) is None


def test_promotion_verdict_true_when_close_pass_rate_and_cheap():
    baseline = {"pass_rate": 0.90, "cost_unknown": False, "cost_microcents_per_case": 100.0}
    candidate = {"pass_rate": 0.89, "cost_unknown": False, "cost_microcents_per_case": 50.0}
    assert routing_report.promotion_verdict(baseline, candidate) is True


def test_promotion_verdict_false_when_pass_rate_drops_too_much():
    baseline = {"pass_rate": 0.90, "cost_unknown": False, "cost_microcents_per_case": 100.0}
    candidate = {"pass_rate": 0.80, "cost_unknown": False, "cost_microcents_per_case": 10.0}
    assert routing_report.promotion_verdict(baseline, candidate) is False


def test_promotion_verdict_false_when_not_cheap_enough():
    baseline = {"pass_rate": 0.90, "cost_unknown": False, "cost_microcents_per_case": 100.0}
    candidate = {"pass_rate": 0.90, "cost_unknown": False, "cost_microcents_per_case": 70.0}
    assert routing_report.promotion_verdict(baseline, candidate) is False


def test_promotion_verdict_none_when_cost_unknown():
    baseline = {"pass_rate": 0.90, "cost_unknown": True, "cost_microcents_per_case": None}
    candidate = {"pass_rate": 0.90, "cost_unknown": False, "cost_microcents_per_case": 1.0}
    assert routing_report.promotion_verdict(baseline, candidate) is None


def test_run_candidate_live_rejects_task_without_a_live_runner():
    with pytest.raises(ValueError, match="no live routing runner"):
        routing_report.run_candidate_live("digest", "groq:some-model")


def test_run_candidate_live_rejects_malformed_candidate():
    with pytest.raises(ValueError, match="provider:model"):
        routing_report.run_candidate_live("ask", "not-a-provider-model")


@pytest.mark.django_db
def test_build_report_offline_only_has_no_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(routing_report, "RESULTS_DIR", tmp_path)
    report = routing_report.build_report("ask", "groq:does-not-exist-yet")
    assert report["candidate"] is None
    assert report["candidate_live"] is False
    assert report["promote"] is None
    assert report["baseline"]["model"] == "anthropic:claude-opus-4-8"


@pytest.mark.django_db
def test_write_report_then_reread_picks_up_prior_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(routing_report, "RESULTS_DIR", tmp_path)
    candidate = "groq:meta-llama/llama-4-scout-17b-16e-instruct"
    live_scoreboard = {"task": "ask", "model": candidate, "cases_total": 5, "cases_graded": 5,
                       "pass_rate": 0.95, "cost_microcents_per_case": 3.0, "cost_unknown": False,
                       "results": []}
    first = routing_report.build_report("ask", candidate, candidate_scoreboard=live_scoreboard)
    path = routing_report.write_report(first, candidate)
    assert path.exists()

    reread = routing_report.build_report("ask", candidate)
    assert reread["candidate_live"] is False
    assert reread["candidate"]["pass_rate"] == 0.95
    assert reread["promote"] is True  # 3.0 <= 60% of the real ask baseline cost


@pytest.mark.django_db
def test_eval_routing_command_offline_writes_report(tmp_path, monkeypatch):
    monkeypatch.setattr(routing_report, "RESULTS_DIR", tmp_path)
    out = StringIO()
    call_command("eval_routing", "--task", "ask",
                 "--candidate", "groq:meta-llama/llama-4-scout-17b-16e-instruct", stdout=out)
    output = out.getvalue()
    assert "pass_rate" in output
    assert "NOT ENOUGH DATA" in output
    assert list(tmp_path.glob("routing_ask_*.json"))


def test_eval_routing_command_requires_enabled_for_live(monkeypatch):
    monkeypatch.setattr(assistant_client, "enabled", lambda: False)
    with pytest.raises(CommandError, match="ASSISTANT_ENABLED"):
        call_command("eval_routing", "--task", "ask", "--candidate", "groq:x", "--yes-live")
