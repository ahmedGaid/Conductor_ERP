"""Deterministic offline graders for golden dataset cases (ai-reliability T1.6), plus the
LLM-as-judge grader for free-text rubrics (T1.7).

The deterministic graders are pure functions of ``(case, output)`` — no DB, no provider, no
randomness, so a given recording always grades the same way. ``grade()`` (used by the offline
runner) still reports ``judge`` cases as ``needs_judge`` — judging needs a live model call, which
would break the runner's zero-network guarantee. ``grade_judge()`` is the real judge grader: called
directly by ``manage.py calibrate_judge`` and any future live judge run, and unit-tested by
injecting a fake ``judge_call`` so it never needs network either.
"""
from __future__ import annotations

import json

from ..errors import AssistantUnavailableError
from ..services import llm as llm_service
from ..services.prompt_registry import get as get_prompt
from .. import client as assistant_client

_TYPE_MAP = {
    "string": str, "integer": int, "number": (int, float), "boolean": bool,
    "array": list, "object": dict, "null": type(None),
}


def _answer_text(output: dict) -> str:
    """Best-effort text to substring-match: the phrased answer, or the raw output as a fallback
    (e.g. an extraction proposal has no "answer" key)."""
    answer = output.get("answer")
    if isinstance(answer, str) and answer:
        return answer
    return json.dumps(output, ensure_ascii=False)


def grade_contains(case: dict, output: dict) -> tuple[bool, str]:
    text = _answer_text(output)
    missing = [s for s in case["expected"]["contains"] if s not in text]
    if missing:
        return False, f"missing substrings: {missing}"
    return True, ""


def grade_citations(case: dict, output: dict) -> tuple[bool, str]:
    got = {str(c.get("value")) for c in output.get("citations") or []}
    missing = [cid for cid in case["expected"]["citations"] if cid not in got]
    if missing:
        return False, f"missing citation ids: {missing} (got {sorted(got)})"
    return True, ""


def grade_refusal(case: dict, output: dict) -> tuple[bool, str]:
    if output.get("used_tool") is not None:
        return False, f"expected a refusal but tool {output['used_tool']!r} ran"
    if not _answer_text(output).strip():
        return False, "expected a refusal message, got an empty answer"
    return True, ""


def _check_type(value, expected_type) -> bool:
    types = expected_type if isinstance(expected_type, list) else [expected_type]
    return any(isinstance(value, _TYPE_MAP.get(t, object)) for t in types)


def _validate_schema(value, schema: dict, path: str = "$") -> list[str]:
    """Minimal JSON-schema subset (type / required / properties / items) — the golden dataset's
    ``schema`` cases only use these, so a hand-rolled check avoids adding the ``jsonschema``
    dependency for one grader."""
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type and not _check_type(value, expected_type):
        errors.append(f"{path}: expected type {expected_type}, got {type(value).__name__}")
        return errors  # further checks are meaningless on a type mismatch
    if isinstance(value, dict) and (expected_type == "object" or "object" in (expected_type or [])):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        for key, subschema in (schema.get("properties") or {}).items():
            if key in value:
                errors.extend(_validate_schema(value[key], subschema, f"{path}.{key}"))
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errors.extend(_validate_schema(item, schema["items"], f"{path}[{i}]"))
    return errors


def grade_schema(case: dict, output: dict) -> tuple[bool, str]:
    errors = _validate_schema(output, case["expected"]["schema"])
    if errors:
        return False, "; ".join(errors)
    return True, ""


_JUDGE_SCHEMA = {
    "type": "object", "required": ["pass", "reason"],
    "properties": {"pass": {"type": "boolean"}, "reason": {"type": "string"}},
}

# Cheapest tier, cross-provider: never the model under test. Tried in order; first provider that
# returns a parseable response wins.
_JUDGE_PROVIDERS = ("gemini", "groq")


def _default_judge_call(system: str, user: str) -> dict:
    """Live judge call, traced under ``feature="eval"`` so eval spend is visible and separable
    from the traffic it grades. Not used by the offline runner — only by ``calibrate_judge`` and
    any future opt-in live judge run."""
    from ..services.tracing import estimate_tokens, trace_call

    last_exc: Exception | None = None
    for prov in _JUDGE_PROVIDERS:
        runner = llm_service._RUNNERS[prov]
        with trace_call("eval", prompt_ref=get_prompt("eval_judge").ref) as handle:
            try:
                text = runner(system, user, _JUDGE_SCHEMA, None, assistant_client.model_id(prov))
            except Exception as exc:  # provider down/unauthenticated — try the next one
                handle.fail(exc.__class__.__name__)
                last_exc = exc
                continue
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                last_exc = exc
                continue
            handle.usage(provider=prov, model=assistant_client.model_id(prov), estimated=True,
                         input_tokens=estimate_tokens(system + user), output_tokens=estimate_tokens(text))
            return parsed
    raise AssistantUnavailableError(
        data={"reason": last_exc.__class__.__name__ if last_exc else "no_judge_provider"})


def grade_judge(case: dict, output: dict, *, judge_call=None) -> tuple[bool, str]:
    """Grade a free-text answer against its rubric via an LLM judge. ``judge_call`` (optional) is
    ``(system, user) -> {"pass": bool, "reason": str}`` — injected by tests with a recorded judge
    output so this stays offline-testable; defaults to a real live call."""
    judge_call = judge_call or _default_judge_call
    prompt = get_prompt("eval_judge")
    system = prompt.render(
        rubric=case["expected"]["judge"],
        case_input=json.dumps(case["input"], ensure_ascii=False),
        answer=_answer_text(output),
    )
    result = judge_call(system, "Grade the answer above against the rubric.")
    return bool(result.get("pass")), str(result.get("reason", ""))


GRADERS = {
    "contains": grade_contains,
    "citations": grade_citations,
    "refusal": grade_refusal,
    "schema": grade_schema,
}


def grade(case: dict, output: dict) -> tuple[str, str]:
    """Grade one case's output. Returns ``(status, reason)`` — status is ``pass`` | ``fail`` |
    ``needs_judge`` (the rubric-graded ``judge`` kind, deferred to T1.7)."""
    expected = case["expected"]
    if "judge" in expected:
        return "needs_judge", ""
    kind = next(k for k in ("schema", "contains", "citations", "refusal") if k in expected)
    passed, reason = GRADERS[kind](case, output)
    return ("pass" if passed else "fail"), reason
