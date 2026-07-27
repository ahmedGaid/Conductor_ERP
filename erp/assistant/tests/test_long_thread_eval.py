"""ai-reliability T3.7 — the long-thread continuity eval suite end to end.

Dataset-shape checks guard the committed fixture; the DB test runs the real suite (seed → drive
summarization to convergence → run one real ``agent.run`` round → check the planted fact reached
the constructed prompt) and asserts every case passes.
"""
from __future__ import annotations

import pytest

from erp.assistant.evals import long_thread

pytestmark = pytest.mark.django_db


def test_dataset_has_five_cases_with_unique_ids_and_key_facts_in_turn_three():
    cases = long_thread.load_cases()
    assert len(cases) == 5
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    assert sum(1 for c in cases if c["lang"] == "ar") == 3
    assert sum(1 for c in cases if c["lang"] == "en") == 2
    for c in cases:
        assert c["key_fact"] in c["turns"][2]["content"], f"{c['id']}: fact not in turn index 2"
        assert c["key_fact"] not in c["question"], f"{c['id']}: question should not restate the fact"
        # Long enough that summarization's own trigger thresholds actually fire during the suite.
        assert len(c["turns"]) > long_thread.summarize.TAIL_MESSAGES + long_thread.summarize.STALE_MESSAGE_GAP


def test_long_thread_suite_passes_every_case():
    board = long_thread.score_suite()
    assert board["total"] == 5
    failed = [r["id"] for r in board["results"] if r["status"] != "pass"]
    assert not failed, f"long-thread continuity cases failed: {failed}"
    assert board["pass_rate"] == 1.0


def test_fact_reaches_the_prompt_via_the_summary_not_raw_history():
    """The interesting claim isn't just "the fact was found" — it's that it survived specifically
    because the summary carried it forward past the raw-history tail boundary."""
    board = long_thread.score_suite()
    assert all(r["found_via_summary"] for r in board["results"])
