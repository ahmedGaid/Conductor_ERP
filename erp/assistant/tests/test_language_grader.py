"""Language-adherence grader — the check that was missing when it was needed.

A live re-record found gemini-2.5-flash answering English questions entirely in Arabic in 21/21
cases. Every one of those graded GREEN, because the only assertion was a money substring the model
had rendered correctly. This grader closes that hole: content being right is no longer enough.
"""
from __future__ import annotations

import pytest

from erp.assistant.evals import graders


def _case(lang: str, expected: dict | None = None) -> dict:
    return {"id": f"t_{lang}", "lang": lang, "feature": "ask",
            "input": {"message": "q"}, "expected": expected or {"contains": ["17,500.00 EGP"]}}


# --- dominant_script -----------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Total sales for July 2026: 17,500.00 EGP across 25 orders.", "en"),
    ("إجمالي المبيعات لهذا الشهر 17,500.00 جنيه مصري (25 أمر بيع).", "ar"),
    # The regression that motivated all this: an English question answered in Arabic.
    ("إجمالي المبيعات لهذا الشهر 17,500.00 EGP.", "ar"),
    # A correct English answer carrying an Arabic proper noun must read as English — majority
    # test, not "contains any Arabic". This exact shape produced false positives in the ad-hoc
    # script that first measured adherence.
    ("Found sales order SO-2026-0034 for customer عميل تجريبي with total 500.00 EGP.", "en"),
    ("5,450.00 EGP", None),   # too few letters to judge
    ("", None),
    ("123 456", None),
])
def test_dominant_script(text, expected):
    assert graders.dominant_script(text) == expected


# --- grade_language ------------------------------------------------------------------------------

def test_arabic_answer_to_english_question_fails():
    passed, reason = graders.grade_language(
        _case("en"), {"answer": "إجمالي المبيعات لهذا الشهر 17,500.00 EGP (25 أمر بيع)."})
    assert not passed
    assert "answered in 'ar'" in reason and "was 'en'" in reason


def test_english_answer_to_arabic_question_fails():
    passed, reason = graders.grade_language(
        _case("ar"), {"answer": "Total sales for July 2026: 17,500.00 EGP across 25 orders."})
    assert not passed
    assert "answered in 'en'" in reason


@pytest.mark.parametrize("lang,answer", [
    ("en", "Total sales for July 2026: 17,500.00 EGP across 25 orders."),
    ("ar", "إجمالي المبيعات لهذا الشهر 17,500.00 EGP (25 أمر بيع)."),
    ("en", "Found sales order SO-2026-0034 for customer عميل تجريبي with total 500.00 EGP."),
    ("ar", "5,450.00 EGP"),          # too short to classify — never invent a failure
    ("en", "5,450.00 EGP"),
])
def test_matching_language_passes(lang, answer):
    passed, _ = graders.grade_language(_case(lang), {"answer": answer})
    assert passed


def test_structured_output_is_skipped():
    """Extraction/schema cases hold structured output, not prose — nothing to judge."""
    passed, _ = graders.grade_language(_case("ar", {"schema": {"type": "object"}}),
                                       {"total_minor": 1750000, "currency": "EGP"})
    assert passed


# --- wiring into grade() -------------------------------------------------------------------------

def test_right_content_in_the_wrong_language_now_fails():
    """The exact regression: the money substring is present and correct, the language is not.

    Before this grader existed, this case graded 'pass'.
    """
    case = _case("en")
    output = {"answer": "إجمالي المبيعات لهذا الشهر 17,500.00 EGP (25 أمر بيع).", "citations": []}

    assert graders.grade_contains(case, output)[0], "content check still passes — that was the trap"
    status, reason = graders.grade(case, output)
    assert status == "fail"
    assert "answered in 'ar'" in reason


def test_content_failure_is_reported_over_language_failure():
    """Wrong content AND wrong language: the content reason is the more actionable one."""
    status, reason = graders.grade(_case("en"), {"answer": "لا توجد بيانات متاحة لهذا الشهر."})
    assert status == "fail"
    assert "missing substrings" in reason


def test_right_content_and_right_language_passes():
    status, reason = graders.grade(
        _case("en"), {"answer": "Total sales for July 2026: 17,500.00 EGP across 25 orders."})
    assert status == "pass"
    assert reason == ""


def test_refusal_case_still_language_checked():
    case = {"id": "r", "lang": "en", "feature": "agent", "input": {"message": "q"},
            "expected": {"refusal": True}}
    output = {"answer": "لا يمكنني المساعدة في هذا الطلب.", "used_tool": None}

    assert graders.grade_refusal(case, output)[0]
    assert graders.grade(case, output)[0] == "fail"
