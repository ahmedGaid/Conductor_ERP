"""T1.6 smoke test: the offline eval runner grades real cases from real recordings (zero network),
and correctly FAILS a case whose recording was deliberately corrupted — a wrong recording must
fail its grader, not silently pass. Marker ``evals`` — green in CI, non-blocking threshold for now
(the golden dataset can grow ahead of the recordings that exercise it)."""
from __future__ import annotations

import time
from io import StringIO

import pytest
from django.core.management import call_command

from erp.assistant.evals import loader, runner

pytestmark = pytest.mark.evals

RECORDED_IDS = [
    "ask_sales_summary_ar_01", "ask_top_customers_ar_01", "refusal_ar_01", "agent_multi_tool_ar_01",
]


@pytest.mark.django_db
def test_run_case_grades_every_recorded_case_as_pass():
    cases = {c["id"]: c for c in loader.load_cases()}
    for case_id in RECORDED_IDS:
        recording = runner.load_recording(case_id)
        assert recording is not None, f"missing recording fixture for {case_id}"
        result = runner.run_case(cases[case_id], recording)
        assert result["status"] == "pass", result


@pytest.mark.django_db
def test_a_deliberately_wrong_recording_fails_its_grader():
    """Negative test (T1.6 accept criterion): a recording that contradicts its case's fixtures
    must be graded ``fail``, never silently pass."""
    case = {
        "id": "eval_negative_test_case", "lang": "en", "feature": "ask",
        "input": {"message": "What is the total sales this month?"},
        "fixtures": {"sales_summary": {"period": "this_month", "total_minor": 1250000,
                                       "count": 18, "total": "12,500.00 EGP"}},
        "expected": {"contains": ["12,500.00 EGP"]},
    }
    wrong_recording = {
        "json_responses": [
            {"tool": "sales_summary", "period": "this_month"},
            {"answer": "Total sales this month were 9,999.00 EGP."},  # deliberately wrong
        ],
        "stream_responses": [],
    }
    result = runner.run_case(case, wrong_recording)
    assert result["status"] == "fail"
    assert "12,500.00 EGP" in result["reason"]


@pytest.mark.django_db
def test_run_evals_command_completes_offline_under_90s():
    out = StringIO()
    started = time.monotonic()
    call_command("run_evals", stdout=out)
    elapsed = time.monotonic() - started
    assert elapsed < 90
    output = out.getvalue()
    assert "pass_rate" in output
    # "recorded" count reflects however many golden cases have a recording fixture on disk today
    # (grows over time, e.g. T1.10's baseline capture) -- only assert the smoke set is covered.
    import re

    match = re.search(r"recorded: (\d+)", output)
    assert match and int(match.group(1)) >= len(RECORDED_IDS)
