"""Routing report (ai-reliability T2.4): compares a task class's current baseline model against a
candidate model on the golden eval set — pass rate and an estimated cost/case — and applies the
promotion rule documented next to ``ASSISTANT_ROUTING`` in settings: a candidate may become
primary for a task only if its pass rate is within 2 points of baseline AND its cost/case is at
most 60% of baseline's.

Two halves, both zero-network unless explicitly asked to spend:
  - the BASELINE side always runs offline against ``evals/recordings/`` (the same machinery
    ``manage.py run_evals`` uses) — no key, no ``--yes-live``, no spend required.
  - the CANDIDATE side needs a live run (``run_candidate_live``) — gated the same way as
    ``record_evals``/``calibrate_judge`` (``ASSISTANT_ENABLED`` + an explicit opt-in, enforced by
    the ``eval_routing`` management command, not here) — unless a prior live run's saved report is
    being re-read for a fresh printout, which needs nothing at all.

Cost is estimated with the same ``estimate_tokens`` heuristic ``services.tracing`` falls back to
when a provider doesn't report real usage, priced via that module's ``PRICING`` table — applied
identically to both sides so the comparison stays apples-to-apples even though it's an estimate,
not billed usage. A model missing from ``PRICING`` reports ``cost_unknown=True`` rather than a
guessed cost, same discipline as ``services.tracing._cost_microcents``.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from django.conf import settings

from ..services.tracing import PRICING, estimate_tokens
from . import graders, loader
from . import runner as eval_runner

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# The promotion rule — mirrored in the ASSISTANT_ROUTING settings comment.
PASS_RATE_TOLERANCE = 0.02
MAX_COST_RATIO = 0.60

# Live routing runs are only wired for the two conversational task classes that have both a real
# service function and golden-case coverage. Extraction stays on the strongest model per the
# roadmap (Phase 5 territory, not an eval-gated candidate today). ``digest``/``suggest``/``judge``/
# ``chat``/``eval`` have no live-comparable service call site yet (``suggest`` has no service at
# all; ``digest``/``judge`` aren't threaded through the gateway with those feature labels) — their
# ASSISTANT_ROUTING entries stay placeholders until one exists.
_LIVE_TASK_TO_FEATURE = {"ask": "ask", "agent_plan": "agent", "agent_answer": "agent"}


def _safe_name(value: str) -> str:
    return value.replace(":", "_").replace("/", "_")


def report_path(task: str, candidate: str) -> Path:
    return RESULTS_DIR / f"routing_{_safe_name(task)}_{_safe_name(candidate)}.json"


def baseline_model_for(task: str) -> str:
    """The current primary ``provider:model`` for a task class, per ``ASSISTANT_ROUTING``."""
    chain = settings.ASSISTANT_ROUTING.get(task)
    if not chain:
        raise ValueError(f"{task!r} is not a task class in settings.ASSISTANT_ROUTING")
    return chain[0]


def _bare_model(provider_model: str) -> str:
    return provider_model.split(":", 1)[1] if ":" in provider_model else provider_model


def _recording_output_text(case_id: str) -> str:
    recording = eval_runner.load_recording(case_id)
    if not recording:
        return ""
    parts = [json.dumps(r, ensure_ascii=False) for r in recording.get("json_responses", [])]
    parts.extend(recording.get("stream_responses", []))
    return "".join(parts)


def _avg_cost_microcents(cases: list[dict], provider_model: str, *,
                         output_text_by_id: dict[str, str]) -> tuple[float | None, bool]:
    """Average estimated cost per case, over cases that have output text captured. ``(None, True)``
    when the model isn't in ``PRICING`` — never guessed."""
    price = PRICING.get(_bare_model(provider_model))
    if not price:
        return None, True
    in_price, out_price = price
    costs = []
    for case in cases:
        text = output_text_by_id.get(case["id"], "")
        if not text:
            continue
        input_tokens = estimate_tokens(case["input"].get("message", ""))
        output_tokens = estimate_tokens(text)
        costs.append(input_tokens * in_price / 1000 + output_tokens * out_price / 1000)
    if not costs:
        return None, False
    return sum(costs) / len(costs), False


def offline_scoreboard(task: str) -> dict:
    """The baseline side: grades every golden case for ``task`` against its existing recording —
    the exact same offline machinery ``manage.py run_evals`` uses, zero network. ``pass_rate`` is
    ``None`` (not the ``1.0`` ``runner.run_all`` reports for an empty graded set — that default
    suits "nothing failed yet", not "nothing was measured") when no case could be graded, e.g. a
    task with golden cases but no offline runner yet (``suggest``)."""
    cases = [c for c in loader.load_cases() if c["feature"] == task]
    scoreboard = eval_runner.run_all(cases) if cases else {
        "total_cases": 0, "recorded_cases": 0, "skipped_no_recording": 0,
        "pass": 0, "fail": 0, "needs_judge": 0, "no_runner": 0, "error": 0, "results": [],
    }
    graded = scoreboard["pass"] + scoreboard["fail"]
    pass_rate = scoreboard["pass"] / graded if graded else None
    output_text_by_id = {c["id"]: _recording_output_text(c["id"]) for c in cases}
    cost, cost_unknown = _avg_cost_microcents(cases, baseline_model_for(task),
                                              output_text_by_id=output_text_by_id)
    return {
        "task": task, "model": baseline_model_for(task), "cases_total": len(cases),
        "cases_graded": graded, "pass_rate": pass_rate,
        "cost_microcents_per_case": cost, "cost_unknown": cost_unknown,
        "raw": scoreboard,
    }


def _live_ask(case: dict, *, actor):
    from ..services import ask as ask_service
    from .runner import _page_from_input

    return ask_service.answer_question(
        question=case["input"]["message"], actor=actor, conversation=None,
        page=_page_from_input(case["input"]))


def _live_agent(case: dict, *, actor):
    from .. import models as assistant_models
    from ..services import agent as agent_service
    from .runner import _page_from_input

    conversation = assistant_models.Conversation.objects.create(user=actor)
    try:
        events = list(agent_service.run(
            actor=actor, conversation=conversation, question=case["input"]["message"],
            page=_page_from_input(case["input"])))
        done = next(e for e in reversed(events) if e["type"] == "done")
        citations_event = next((e for e in events if e["type"] == "citations"), {"citations": []})
        answer_text = "".join(e["text"] for e in events if e["type"] == "token")
        return {"answer": answer_text, "citations": citations_event["citations"],
                "used_tool": done.get("used_tool")}
    finally:
        conversation.delete()


_LIVE_RUNNERS = {"ask": _live_ask, "agent": _live_agent}


def run_candidate_live(task: str, candidate: str, *, actor=None) -> dict:
    """Run the task's golden subset LIVE against ``candidate`` ("provider:model") and grade with
    the real graders — makes real, billed provider calls. The caller (the ``eval_routing``
    management command) is responsible for confirming ``ASSISTANT_ENABLED`` and an explicit
    ``--yes-live`` before calling this; it isn't re-checked here so this stays directly testable
    with a monkeypatched provider."""
    feature = _LIVE_TASK_TO_FEATURE.get(task)
    if feature is None:
        raise ValueError(
            f"{task!r} has no live routing runner yet — only {sorted(_LIVE_TASK_TO_FEATURE)} do")
    prov, _, model = candidate.partition(":")
    if not model:
        raise ValueError(f"candidate must be 'provider:model', got {candidate!r}")

    cases = [c for c in loader.load_cases() if c["feature"] == feature]
    if not cases:
        raise ValueError(f"no golden cases for feature {feature!r}")

    actor = actor or eval_runner.eval_actor()
    live_runner = _LIVE_RUNNERS[feature]

    from ..gateway import core as gateway_core

    saved_chain, saved_model = gateway_core.provider_chain, gateway_core.model_id
    results: list[dict] = []
    output_text_by_id: dict[str, str] = {}
    try:
        gateway_core.provider_chain = lambda: [prov]
        gateway_core.model_id = lambda p=None: model
        for case in cases:
            started = time.monotonic()
            with eval_runner.patched_tools(case["fixtures"]):
                try:
                    output = live_runner(case, actor=actor)
                except Exception as exc:  # a real provider/tool failure is a graded failure
                    results.append({"id": case["id"], "status": "error",
                                    "reason": f"{exc.__class__.__name__}: {exc}",
                                    "latency_ms": int((time.monotonic() - started) * 1000)})
                    continue
            output_text_by_id[case["id"]] = json.dumps(output, ensure_ascii=False)
            status, reason = graders.grade(case, output)
            if status == "needs_judge":
                passed, reason = graders.grade_judge(case, output)
                status = "pass" if passed else "fail"
            results.append({"id": case["id"], "status": status, "reason": reason,
                            "latency_ms": int((time.monotonic() - started) * 1000)})
    finally:
        gateway_core.provider_chain, gateway_core.model_id = saved_chain, saved_model

    graded = [r for r in results if r["status"] in ("pass", "fail")]
    passed = sum(1 for r in graded if r["status"] == "pass")
    pass_rate = passed / len(graded) if graded else None
    cost, cost_unknown = _avg_cost_microcents(cases, candidate, output_text_by_id=output_text_by_id)
    return {
        "task": task, "model": candidate, "cases_total": len(cases), "cases_graded": len(graded),
        "pass_rate": pass_rate, "cost_microcents_per_case": cost, "cost_unknown": cost_unknown,
        "results": results,
    }


def promotion_verdict(baseline: dict, candidate: dict | None) -> bool | None:
    """``True``/``False`` once both sides have a real pass rate and a priced cost; ``None`` when
    there isn't enough evidence yet (candidate not run live, or either model unpriced) — never
    guessed, same discipline as the cost estimate it depends on."""
    if candidate is None:
        return None
    if baseline["pass_rate"] is None or candidate["pass_rate"] is None:
        return None
    if baseline["cost_unknown"] or candidate["cost_unknown"]:
        return None
    if not baseline["cost_microcents_per_case"] or candidate["cost_microcents_per_case"] is None:
        return None
    pass_ok = candidate["pass_rate"] >= baseline["pass_rate"] - PASS_RATE_TOLERANCE
    cost_ok = candidate["cost_microcents_per_case"] <= baseline["cost_microcents_per_case"] * MAX_COST_RATIO
    return bool(pass_ok and cost_ok)


def build_report(task: str, candidate: str, *, candidate_scoreboard: dict | None = None) -> dict:
    """Assemble the full baseline-vs-candidate report. ``candidate_scoreboard`` is the dict
    ``run_candidate_live`` returns — omit it for a baseline-only report (fully offline; the
    candidate side reads back a prior live report file for the same task+candidate if one exists,
    so a report can be reprinted without re-spending)."""
    baseline = offline_scoreboard(task)
    candidate_report = candidate_scoreboard
    if candidate_report is None:
        prior = report_path(task, candidate)
        if prior.exists():
            candidate_report = json.loads(prior.read_text(encoding="utf-8")).get("candidate")
    return {
        "task": task, "baseline": baseline, "candidate": candidate_report,
        "candidate_live": candidate_scoreboard is not None,
        "promote": promotion_verdict(baseline, candidate_report),
        "rule": f"candidate pass_rate >= baseline - {PASS_RATE_TOLERANCE:.0%} AND "
                f"cost/case <= {MAX_COST_RATIO:.0%} of baseline",
    }


def write_report(report: dict, candidate: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = report_path(report["task"], candidate)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
