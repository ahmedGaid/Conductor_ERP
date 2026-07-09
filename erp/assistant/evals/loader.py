"""Loads and structurally validates golden_v1.jsonl cases (ai-reliability T1.5). No DB, no
provider — pure file I/O, safe to import from tests or the future offline runner (T1.6)."""
from __future__ import annotations

import json
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
GOLDEN_V1_PATH = DATASETS_DIR / "golden_v1.jsonl"

REQUIRED_KEYS = {"id", "lang", "feature", "input", "fixtures", "expected"}
VALID_LANGS = {"ar", "en"}
VALID_FEATURES = {"ask", "agent", "extract", "suggest"}
EXPECTED_KIND_KEYS = {"schema", "contains", "citations", "refusal", "judge"}


class CaseValidationError(ValueError):
    """Raised for a structurally invalid case — id included for a fast fix."""


def _validate_case(case: dict) -> None:
    case_id = case.get("id", "<missing id>")
    missing = REQUIRED_KEYS - case.keys()
    if missing:
        raise CaseValidationError(f"case {case_id!r} missing keys: {sorted(missing)}")
    if case["lang"] not in VALID_LANGS:
        raise CaseValidationError(f"case {case_id!r} has invalid lang: {case['lang']!r}")
    if case["feature"] not in VALID_FEATURES:
        raise CaseValidationError(f"case {case_id!r} has invalid feature: {case['feature']!r}")
    if not isinstance(case["input"], dict) or not case["input"]:
        raise CaseValidationError(f"case {case_id!r} input must be a non-empty object")
    if not isinstance(case["fixtures"], dict):
        raise CaseValidationError(f"case {case_id!r} fixtures must be an object")
    expected = case["expected"]
    if not isinstance(expected, dict):
        raise CaseValidationError(f"case {case_id!r} expected must be an object")
    kind_keys = EXPECTED_KIND_KEYS & expected.keys()
    if len(kind_keys) != 1:
        raise CaseValidationError(
            f"case {case_id!r} expected must have exactly one of {sorted(EXPECTED_KIND_KEYS)}, "
            f"got {sorted(kind_keys)}"
        )
    kind = next(iter(kind_keys))
    value = expected[kind]
    if kind in ("contains", "citations") and (
        not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value)
    ):
        raise CaseValidationError(f"case {case_id!r} expected.{kind} must be a non-empty list of strings")
    if kind == "schema" and not isinstance(value, dict):
        raise CaseValidationError(f"case {case_id!r} expected.schema must be an object")
    if kind == "refusal" and value is not True:
        raise CaseValidationError(f"case {case_id!r} expected.refusal must be true")
    if kind == "judge" and not isinstance(value, str):
        raise CaseValidationError(f"case {case_id!r} expected.judge must be a string")


def load_cases(path: Path = GOLDEN_V1_PATH) -> list[dict]:
    """Parse + structurally validate every line; raises on the first bad case."""
    cases: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CaseValidationError(f"line {lineno} is not valid JSON: {exc}") from exc
        _validate_case(case)
        cases.append(case)
    return cases
