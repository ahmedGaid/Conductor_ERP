"""LLM-as-judge grader (ai-reliability T1.7): offline-testable via an injected ``judge_call`` — no
network. ``calibrate_judge`` is live-only and must refuse to run without ``--yes-live``."""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from erp.assistant.evals import graders

CASE = {
    "input": {"message": "How many units of SKU-118 do we have?"},
    "expected": {"judge": "Answer states the current stock level for SKU-118 without inventing a number."},
}


def test_grade_judge_passes_on_recorded_judge_pass():
    recorded_judge_output = {"pass": True, "reason": "States 42 units, matches the record."}
    passed, reason = graders.grade_judge(
        CASE, {"answer": "SKU-118 has 42 units in stock."},
        judge_call=lambda system, user: recorded_judge_output,
    )
    assert passed is True
    assert reason == "States 42 units, matches the record."


def test_grade_judge_fails_on_recorded_judge_fail():
    recorded_judge_output = {"pass": False, "reason": "No stock figure given."}
    passed, reason = graders.grade_judge(
        CASE, {"answer": "SKU-118 is well stocked."},
        judge_call=lambda system, user: recorded_judge_output,
    )
    assert passed is False
    assert reason == "No stock figure given."


def test_grade_judge_renders_rubric_and_answer_into_the_prompt():
    captured = {}

    def fake_judge_call(system, user):
        captured["system"] = system
        return {"pass": True, "reason": "ok"}

    graders.grade_judge(CASE, {"answer": "SKU-118 has 42 units in stock."}, judge_call=fake_judge_call)
    assert CASE["expected"]["judge"] in captured["system"]
    assert "SKU-118 has 42 units in stock." in captured["system"]


def test_calibration_dataset_is_well_formed():
    path = (Path(graders.__file__).resolve().parent / "datasets" / "calibration_v1.jsonl")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 30
    assert sum(1 for r in rows if r["lang"] == "ar") == 15
    assert sum(1 for r in rows if r["lang"] == "en") == 15
    assert sum(1 for r in rows if r["expected_pass"] is True) == 15
    assert sum(1 for r in rows if r["expected_pass"] is False) == 15
    assert len({r["id"] for r in rows}) == len(rows)


@pytest.mark.django_db
def test_calibrate_judge_refuses_without_yes_live(settings):
    settings.ASSISTANT_ENABLED = True
    with pytest.raises(CommandError, match="--yes-live"):
        call_command("calibrate_judge", stdout=StringIO())


@pytest.mark.django_db
def test_calibrate_judge_refuses_when_assistant_disabled(settings):
    settings.ASSISTANT_ENABLED = False
    with pytest.raises(CommandError, match="ASSISTANT_ENABLED"):
        call_command("calibrate_judge", "--yes-live", stdout=StringIO())
