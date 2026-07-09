"""Offline eval runner (ai-reliability T1.6): replays a recorded provider response through the
feature's REAL service function — so we're grading actual prompt-building/tool-dispatch/answer
code, not a reimplementation of it — with zero network calls.

Two seams are monkeypatched per case, both restored on exit:
  1. the LLM call (``complete_json`` / ``complete_stream``) is replaced by a ``_Player`` that pops
     the case's recorded responses in call order;
  2. each tool named in the case's ``fixtures`` has its ``.run`` replaced to return the canned
     result instead of touching the DB — ``.cite`` stays real (a pure function of the result), so
     citations are computed exactly as in production.

Recordings live one-per-case at ``evals/recordings/<case_id>.json`` (see ``record_evals`` for how
they're made). A case with no recording file is skipped, not failed — the golden dataset can grow
ahead of the recordings that exercise it. ``feature="suggest"`` has no offline runner yet (no
Python service backs the page-context follow-up chips) and always reports ``no_runner``.
"""
from __future__ import annotations

import dataclasses
import json
import time
from contextlib import contextmanager
from pathlib import Path

from .. import tools as tools_module
from ..services import agent as agent_service
from ..services import ask as ask_service
from ..services import extraction as extraction_service
from . import graders, loader

RECORDINGS_DIR = Path(__file__).resolve().parent / "recordings"


def recording_path(case_id: str) -> Path:
    return RECORDINGS_DIR / f"{case_id}.json"


def load_recording(case_id: str) -> dict | None:
    path = recording_path(case_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class RecordingExhausted(RuntimeError):
    """The case's recording has fewer responses than the real code path asked for."""


class _Player:
    """Plays back one case's recorded responses in call order — the offline stand-in for
    ``complete_json`` / ``complete_stream``. Running out of responses is a hard error: that's a
    scenario needing a fresh recording, not silent reuse of a stale one."""

    def __init__(self, recording: dict):
        self._json = list(recording.get("json_responses", []))
        self._stream = list(recording.get("stream_responses", []))

    def complete_json(self, *args, **kwargs) -> dict:
        if not self._json:
            raise RecordingExhausted("recording has no more json_responses")
        return self._json.pop(0)

    def complete_stream(self, *args, **kwargs):
        if not self._stream:
            raise RecordingExhausted("recording has no more stream_responses")
        yield self._stream.pop(0)


@contextmanager
def _patched_client(player: _Player):
    saved = {
        "ask.complete_json": ask_service.complete_json,
        "agent.complete_json": agent_service.complete_json,
        "agent.complete_stream": agent_service.complete_stream,
    }
    try:
        ask_service.complete_json = player.complete_json
        agent_service.complete_json = player.complete_json
        agent_service.complete_stream = player.complete_stream
        yield
    finally:
        ask_service.complete_json = saved["ask.complete_json"]
        agent_service.complete_json = saved["agent.complete_json"]
        agent_service.complete_stream = saved["agent.complete_stream"]


@contextmanager
def patched_tools(fixtures: dict):
    """Swap the ``.run`` of every tool named in ``fixtures`` for one returning the canned result;
    ``.cite`` is left real. Fixture keys that aren't a tool name (e.g. ``document_text``,
    ``page_context``) are feature-specific payloads, not tools, and are ignored here."""
    targeted = {name: canned for name, canned in fixtures.items() if name in tools_module.TOOLS}
    saved = {name: tools_module.TOOLS[name] for name in targeted}
    try:
        for name, canned in targeted.items():
            tools_module.TOOLS[name] = dataclasses.replace(
                tools_module.TOOLS[name], run=lambda actor, _canned=canned, **kw: _canned)
        yield
    finally:
        tools_module.TOOLS.update(saved)


def eval_actor():
    """A dedicated, idempotent system user for eval runs — a superuser so the real prompt-building
    code (roles/accessible-modules/company context) runs unhindered without seeding RBAC rows."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="ai_eval_runner",
        defaults={"email": "ai-eval-runner@local.invalid", "is_staff": True, "is_superuser": True},
    )
    return user


def _page_from_input(input_: dict) -> dict | None:
    if not input_.get("entity_type"):
        return None
    return {"record": {"type": input_["entity_type"], "id": input_.get("entity_id", ""),
                        "label": input_.get("entity_id", "")}}


def _run_ask(case: dict, recording: dict, *, actor) -> dict:
    with _patched_client(_Player(recording)), patched_tools(case["fixtures"]):
        return ask_service.answer_question(
            question=case["input"]["message"], actor=actor, conversation=None,
            page=_page_from_input(case["input"]),
        )


def _run_agent(case: dict, recording: dict, *, actor) -> dict:
    from .. import models as assistant_models

    conversation = assistant_models.Conversation.objects.create(user=actor)
    try:
        with _patched_client(_Player(recording)), patched_tools(case["fixtures"]):
            events = list(agent_service.run(
                actor=actor, conversation=conversation, question=case["input"]["message"],
                page=_page_from_input(case["input"]),
            ))
        done = next(e for e in reversed(events) if e["type"] == "done")
        citations_event = next((e for e in events if e["type"] == "citations"), {"citations": []})
        answer_text = "".join(e["text"] for e in events if e["type"] == "token")
        return {"answer": answer_text, "citations": citations_event["citations"],
                "used_tool": done.get("used_tool")}
    finally:
        conversation.delete()


def _run_extract(case: dict, recording: dict, *, actor) -> dict:
    """Extraction's real provider call takes raw image/PDF bytes, not text — the golden case only
    carries ``document_text``, so the vision call itself can't be replayed. We force the provider
    and stub its raw ``_extract_<provider>`` function to return the recorded (already-extracted)
    fields, then let the real post-processing (``_proposal``: supplier/line fuzzy-matching, audit)
    run unchanged."""
    saved_provider = extraction_service.provider
    saved_extractor = extraction_service._extract_anthropic
    extracted = recording["json_responses"][0]
    try:
        extraction_service.provider = lambda: "anthropic"
        extraction_service._extract_anthropic = lambda data, media_type: extracted
        return extraction_service.extract_document(
            data=b"", media_type="application/pdf", filename="eval-doc.pdf", actor=actor)
    finally:
        extraction_service.provider = saved_provider
        extraction_service._extract_anthropic = saved_extractor


_FEATURE_RUNNERS = {"ask": _run_ask, "agent": _run_agent, "extract": _run_extract}


def run_case(case: dict, recording: dict, *, actor=None) -> dict:
    """Run one case against its recording and grade the output. Returns ``{id, feature, lang,
    status, reason, latency_ms}`` — status: ``pass`` | ``fail`` | ``needs_judge`` | ``error`` |
    ``no_runner`` (the feature has no offline runner yet, e.g. ``suggest``)."""
    started = time.monotonic()
    runner_fn = _FEATURE_RUNNERS.get(case["feature"])
    if runner_fn is None:
        return {"id": case["id"], "feature": case["feature"], "lang": case["lang"],
                "status": "no_runner",
                "reason": f"no offline runner for feature {case['feature']!r} yet", "latency_ms": 0}
    try:
        output = runner_fn(case, recording, actor=actor if actor is not None else eval_actor())
    except Exception as exc:  # a broken recording/monkeypatch is a graded failure, not a crash
        return {"id": case["id"], "feature": case["feature"], "lang": case["lang"], "status": "error",
                "reason": f"{exc.__class__.__name__}: {exc}",
                "latency_ms": int((time.monotonic() - started) * 1000)}
    status, reason = graders.grade(case, output)
    return {"id": case["id"], "feature": case["feature"], "lang": case["lang"], "status": status,
            "reason": reason, "latency_ms": int((time.monotonic() - started) * 1000)}


def run_all(cases: list[dict] | None = None) -> dict:
    """Grade every case that has a recording; cases without one are counted separately (not in the
    pass rate) so the dataset can grow ahead of the recordings that exercise it."""
    cases = cases if cases is not None else loader.load_cases()
    actor = eval_actor()
    results = []
    skipped_no_recording = 0
    for case in cases:
        recording = load_recording(case["id"])
        if recording is None:
            skipped_no_recording += 1
            continue
        results.append(run_case(case, recording, actor=actor))

    graded = [r for r in results if r["status"] in ("pass", "fail")]
    passed = sum(1 for r in graded if r["status"] == "pass")
    pass_rate = passed / len(graded) if graded else 1.0

    by_feature: dict[str, dict[str, int]] = {}
    by_lang: dict[str, dict[str, int]] = {}
    for r in results:
        by_feature.setdefault(r["feature"], {}).setdefault(r["status"], 0)
        by_feature[r["feature"]][r["status"]] += 1
        by_lang.setdefault(r["lang"], {}).setdefault(r["status"], 0)
        by_lang[r["lang"]][r["status"]] += 1

    return {
        "total_cases": len(cases), "recorded_cases": len(results),
        "skipped_no_recording": skipped_no_recording,
        "pass": passed, "fail": sum(1 for r in graded if r["status"] == "fail"),
        "needs_judge": sum(1 for r in results if r["status"] == "needs_judge"),
        "no_runner": sum(1 for r in results if r["status"] == "no_runner"),
        "error": sum(1 for r in results if r["status"] == "error"),
        "pass_rate": pass_rate,
        "by_feature": by_feature, "by_lang": by_lang,
        "results": results,
    }
