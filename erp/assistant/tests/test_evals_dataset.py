"""Golden dataset v1 (ai-reliability T1.5): every case is schema-valid and the file meets the
roadmap's minimum split — the yardstick later phases (T1.6+) are measured against."""
from __future__ import annotations

from erp.assistant.evals.loader import load_cases

MIN_TOTAL = 150
MIN_AR = 90
MIN_EN = 60
MIN_REFUSAL = 20
MIN_CITATIONS = 20


def test_every_case_is_schema_valid():
    cases = load_cases()
    assert len(cases) >= MIN_TOTAL


def test_ids_are_unique():
    cases = load_cases()
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))


def test_minimum_split_is_met():
    cases = load_cases()
    ar = sum(1 for c in cases if c["lang"] == "ar")
    en = sum(1 for c in cases if c["lang"] == "en")
    refusal = sum(1 for c in cases if "refusal" in c["expected"])
    citations = sum(1 for c in cases if "citations" in c["expected"])
    assert ar >= MIN_AR, f"ar={ar} < {MIN_AR}"
    assert en >= MIN_EN, f"en={en} < {MIN_EN}"
    assert refusal >= MIN_REFUSAL, f"refusal={refusal} < {MIN_REFUSAL}"
    assert citations >= MIN_CITATIONS, f"citations={citations} < {MIN_CITATIONS}"


def test_features_are_all_known():
    cases = load_cases()
    features = {c["feature"] for c in cases}
    assert features <= {"ask", "agent", "extract", "suggest"}
    # at least one case of each feature keeps the split honest across the whole surface
    assert features == {"ask", "agent", "extract", "suggest"}
