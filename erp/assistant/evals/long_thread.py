"""Long-thread continuity eval (ai-reliability T3.7): 5 golden cases (3 ar / 2 en) proving that a
fact planted early in a conversation (the "turn-3" reference the plan describes) is still reachable
by the planner's envelope once the thread has grown well past the raw-history tail and rolling
summarization has kicked in.

There is no live model to grade offline (the whole eval suite runs with zero network — see
``runner.py``), so this can't grade whether a real model *answers correctly* from the fact; it grades
the honest, structurally-testable claim instead: does the CONSTRUCTED PROMPT for the next round
actually carry the fact forward (via the maintained summary once it falls out of the raw tail), the
same "grade the mechanism, not final-answer quality" approach the retrieval suite (T3.3) takes.

Each case seeds a conversation with enough prior messages to clear both trigger thresholds
(``summarize.TAIL_MESSAGES`` + ``summarize.STALE_MESSAGE_GAP``), drives real ``summarize.refresh_summary``
calls to convergence through a deterministic fixture summarizer (a faithful, if simplistic,
pass-through — like ``retrieval.fixture_embed`` stands in for a real embedding model), then runs the
REAL ``agent.run`` for one more turn with the planner's decision captured (not executed) so the
round's actual constructed prompt can be inspected for the planted fact.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.test import override_settings

from .. import models as assistant_models
from ..services import agent as agent_service
from ..services import summarize
from .runner import eval_actor

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
CASES_PATH = DATASETS_DIR / "long_thread_v1.jsonl"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _fixture_summarize(system, user, schema, **kwargs):
    """A deterministic stand-in for the real summarizer model: ``summarize.refresh_summary``
    renders the prior summary + pending turns straight into ``system`` (see prompts/thread_summary.md
    — ``user`` is just the fixed "Update the summary now." instruction, mirroring rerank.py's
    prompt/instruction split). Echoing ``system`` back verbatim faithfully carries every turn's
    content forward rather than truly compressing it — good enough to prove the PIPELINE never
    drops a fact between refreshes; a real model's actual compression quality is not something this
    offline suite can grade (see module docstring)."""
    return {"summary": system}


def _seed_conversation(actor, turns: list[dict]) -> assistant_models.Conversation:
    conversation = assistant_models.Conversation.objects.create(user=actor)
    for turn in turns:
        conversation.messages.create(role=turn["role"], content=turn["content"])
    return conversation


def _drive_summarization(conversation, saved_complete_json) -> None:
    summarize.complete_json = _fixture_summarize
    try:
        guard = 0  # a real bug (e.g. summary_upto_message never advancing) must not hang the suite
        while summarize.should_refresh(conversation) and guard < 20:
            summarize.refresh_summary(conversation)
            guard += 1
    finally:
        summarize.complete_json = saved_complete_json


def run_case(case: dict, *, actor) -> dict:
    conversation = _seed_conversation(actor, case["turns"])
    saved = summarize.complete_json
    try:
        _drive_summarization(conversation, saved)

        captured: dict = {}

        def capture_decision(system, round_user, schema, **kwargs):
            captured["round_user"] = round_user
            return {"action": "answer"}

        saved_agent_json = agent_service.complete_json
        saved_agent_stream = agent_service.complete_stream
        agent_service.complete_json = capture_decision
        agent_service.complete_stream = lambda messages, **_: iter(["(eval stub answer)"])
        try:
            with override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic"):
                list(agent_service.run(actor=actor, conversation=conversation,
                                       question=case["question"], page=None))
        finally:
            agent_service.complete_json = saved_agent_json
            agent_service.complete_stream = saved_agent_stream

        found = case["key_fact"] in captured.get("round_user", "")
        found_via_summary = case["key_fact"] in (conversation.summary or "")
        return {"id": case["id"], "lang": case["lang"], "status": "pass" if found else "fail",
                "found_via_summary": found_via_summary}
    finally:
        conversation.delete()


def score_suite(*, actor=None) -> dict:
    actor = actor or eval_actor()
    results = [run_case(case, actor=actor) for case in load_cases()]
    passed = sum(1 for r in results if r["status"] == "pass")
    return {
        "suite": "long_thread_v1", "offline": True, "total": len(results), "pass": passed,
        "fail": len(results) - passed, "pass_rate": passed / len(results) if results else 1.0,
        "results": results,
    }
