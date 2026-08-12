"""The typed planner (ai-reliability T5.2): a validated Plan object before any tool executes.

Today's loop (``agent.py``) decides one step at a time — the user watches a spinner and finds out
what the assistant is doing only as each step lands. The planner puts the shape of the whole turn
up front: one extra model call returns an ordered list of steps, each naming a real tool from the
registry, which is validated here, persisted on the ``AgentRun``, streamed to the panel as pending
lines, and then walked by the executor.

Three properties matter more than the plan itself:

- **Never a dead end.** An invalid plan is retried ONCE with the validation reasons fed back; still
  invalid (or the call failed, or the model said ``direct``) and the caller falls back to today's
  reactive loop with ``trace.meta.plan_fallback`` recorded. A planner outage degrades the run to
  exactly the behaviour that shipped before this task — never to an error.
- **The registry is the authority, not the model.** ``needs_confirm`` is recomputed from the action
  registry (``requires_confirm``) rather than trusted from the model's JSON, and any step naming a
  tool that isn't in ``TOOLS``/``ACTIONS`` invalidates the plan. The model proposes; the registry
  decides.
- **Purity where it counts.** ``validate`` is a pure function over the raw JSON — every rule below
  is unit-tested without a provider, a database, or a network call.
"""
from __future__ import annotations

import json

from ..gateway.core import complete_json
from ..tools import TOOLS, catalog_text
from . import actions
from .prompt_registry import get as get_prompt
from .tracing import NULL_HANDLE

# The plan's hard ceiling. A turn that genuinely needs more than this is a turn the round cap
# (``agent.MAX_ROUNDS``) would stop anyway — planning further is planning fiction.
MAX_PLAN_STEPS = 8

# How many times a failed step may trigger a fresh plan from the current state before the run
# gives up and answers honestly. Two is enough to route around a bad argument or a missing record;
# more just spends money re-deciding.
MAX_REPLANS = 2

# Fallback reasons recorded on the trace — a small closed vocabulary, so "how often did planning
# fall back, and why" is a query rather than a string search.
FALLBACK_DIRECT = "direct"        # the planner itself said the request needs no plan
FALLBACK_INVALID = "invalid"      # two attempts, still not a valid plan
FALLBACK_ERROR = "error"          # the planner call itself failed (provider/gateway)

_plan_prompt = get_prompt("agent_plan")

_STEP_SCHEMA = {
    "type": "object",
    "properties": {
        "step": {"type": "integer", "description": "1-based position in the plan"},
        "tool": {"type": "string", "description": "an exact tool or action name from the catalog"},
        "args_intent": {"type": "string",
                        "description": "plain words: what this step looks up, and with which values"},
        "why": {"type": "string", "description": "<=8 words, shown to the user"},
        "needs_confirm": {"type": "boolean",
                          "description": "true for a write action (the system overrides this)"},
    },
    "required": ["step", "tool", "args_intent", "why", "needs_confirm"],
    "additionalProperties": False,
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "direct": {"type": "boolean",
                   "description": "true when one step (or none) settles the request — skip planning"},
        "steps": {"type": "array", "items": _STEP_SCHEMA},
    },
    "required": ["direct", "steps"],
    "additionalProperties": False,
}


class PlanStep:
    """One validated step. Deliberately a plain object with ``as_dict`` rather than a dataclass with
    ``asdict``: the dict shape below is the wire/DB shape (``AgentRun.plan``, the SSE ``plan``
    event), so it is written once, here, and never re-derived at each call site."""

    __slots__ = ("step", "tool", "args_intent", "why", "needs_confirm")

    def __init__(self, step: int, tool: str, args_intent: str, why: str, needs_confirm: bool):
        self.step = step
        self.tool = tool
        self.args_intent = args_intent
        self.why = why
        self.needs_confirm = needs_confirm

    def as_dict(self) -> dict:
        return {"step": self.step, "tool": self.tool, "args_intent": self.args_intent,
                "why": self.why, "needs_confirm": self.needs_confirm}

    def __eq__(self, other) -> bool:
        return isinstance(other, PlanStep) and self.as_dict() == other.as_dict()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"PlanStep({self.as_dict()})"


class PlanOutcome:
    """What the planner decided: either steps to walk, or a reason the caller should run the
    reactive loop instead. ``steps`` is non-empty if and only if ``fallback_reason`` is empty."""

    __slots__ = ("steps", "fallback_reason")

    def __init__(self, steps: list[PlanStep] | None = None, fallback_reason: str = ""):
        self.steps = list(steps or [])
        self.fallback_reason = fallback_reason

    @property
    def planned(self) -> bool:
        return bool(self.steps)

    def as_list(self) -> list[dict]:
        return [s.as_dict() for s in self.steps]


def known_tool(name: str) -> bool:
    return name in TOOLS or name in actions.ACTIONS


def registry_needs_confirm(name: str) -> bool:
    """The registry's truth, never the model's: a write action confirms (no action may declare
    otherwise — see ``Action.requires_confirm``), a read-only tool never does."""
    action = actions.ACTIONS.get(name)
    return bool(action.requires_confirm) if action is not None else False


def validate(raw: dict) -> tuple[list[PlanStep], list[str]]:
    """Pure validation of one planner response. Returns ``(steps, reasons)``; ``reasons`` is empty
    only when the plan is usable. A ``direct`` response is valid AND yields no steps — the caller
    reads ``raw["direct"]`` to tell "planned nothing on purpose" from "produced a broken plan".

    Every reason is written for the model, not for a log: it is fed straight back on the retry, so
    it must say what was wrong in terms the model can act on.
    """
    reasons: list[str] = []
    if not isinstance(raw, dict):
        return [], ["The plan must be a JSON object."]
    if raw.get("direct") is True:
        return [], []
    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        return [], ["The plan has no steps. Either set direct=true or give at least one step."]
    if len(raw_steps) > MAX_PLAN_STEPS:
        reasons.append(f"The plan has {len(raw_steps)} steps; at most {MAX_PLAN_STEPS} are allowed.")
    steps: list[PlanStep] = []
    for position, item in enumerate(raw_steps[:MAX_PLAN_STEPS], start=1):
        if not isinstance(item, dict):
            reasons.append(f"Step {position} is not an object.")
            continue
        name = (item.get("tool") or "").strip()
        if not name:
            reasons.append(f"Step {position} names no tool.")
            continue
        if not known_tool(name):
            reasons.append(
                f"Step {position} names '{name}', which is not a tool or action in the catalog. "
                "Use an exact name from the lists you were given.")
            continue
        why = (str(item.get("why") or "").strip() or name.replace("_", " "))
        args_intent = str(item.get("args_intent") or "").strip()
        # Positions are renumbered from the accepted steps, never trusted from the model: a plan
        # that skipped or repeated a number would otherwise desync the executor's cursor.
        steps.append(PlanStep(step=len(steps) + 1, tool=name, args_intent=args_intent, why=why,
                              needs_confirm=registry_needs_confirm(name)))
    if reasons:
        return [], reasons
    if not steps:
        return [], ["No usable step remained in the plan."]
    # A write action is the end of a turn (the confirm card ends it), so anything planned after one
    # can never run. Truncate rather than reject — the plan up to and including it is still good.
    for index, step in enumerate(steps):
        if step.needs_confirm:
            steps = steps[: index + 1]
            break
    return steps, []


def _system() -> str:
    return _plan_prompt.render(catalog=catalog_text(), action_catalog=actions.catalog_text(),
                               max_steps=MAX_PLAN_STEPS)


def _user(question: str, history: list[dict], gathered: list[dict], failure: str) -> str:
    payload: dict = {"question": question}
    if history:
        payload["conversation_so_far"] = history
    if gathered:
        payload["already_gathered"] = gathered
    if failure:
        # A replan: say plainly what just broke so the new plan routes around it instead of
        # re-planning the same failing step.
        payload["previous_step_failed"] = failure
    return json.dumps(payload, ensure_ascii=False)


def make_plan(*, question: str, history: list[dict] | None = None, gathered: list[dict] | None = None,
              media: list | None = None, actor=None, conversation_id=None, trace=NULL_HANDLE,
              failure: str = "", extra_system: str = "") -> PlanOutcome:
    """One planner call (plus at most one repair retry). Never raises: any provider/gateway failure
    becomes a ``FALLBACK_ERROR`` outcome, because a planner that is down must not take the turn
    down with it.

    ``failure`` (a replan) and ``gathered`` (what earlier steps already returned) are what make the
    second and third plans of a run different from the first — the model plans from the current
    state, not from the original question alone.
    """
    system = _system()
    if extra_system:
        # The same page-record / reply-language preamble the loop puts on its own prompt: the plan
        # must resolve "this order" against the page the user is on, exactly as the loop does.
        system = extra_system + system
    user = _user(question, history or [], gathered or [], failure)
    reasons: list[str] = []
    for attempt in (1, 2):
        try:
            raw = complete_json(system, user, PLAN_SCHEMA, media=media, feature="agent_plan",
                                actor=actor, conversation_id=conversation_id,
                                prompt_ref=_plan_prompt.ref)
        except Exception:
            trace.step(kind="validation", name="plan", ok=False, detail={"reason": FALLBACK_ERROR})
            return PlanOutcome(fallback_reason=FALLBACK_ERROR)
        steps, reasons = validate(raw if isinstance(raw, dict) else {})
        if steps:
            trace.step(kind="planner", name="plan", ok=True,
                       detail={"steps": len(steps), "attempt": attempt,
                               "tools": [s.tool for s in steps]})
            return PlanOutcome(steps=steps)
        if not reasons:  # a valid, deliberate "direct" — one step is enough, don't plan it
            trace.step(kind="planner", name="plan", ok=True,
                       detail={"direct": True, "attempt": attempt})
            return PlanOutcome(fallback_reason=FALLBACK_DIRECT)
        if attempt == 1:
            # Repair pass: the same request plus exactly what was wrong with the first answer.
            user = _user(question, history or [], gathered or [], failure) + (
                "\n\nYour previous plan was rejected:\n- " + "\n- ".join(reasons)
                + "\nReturn a corrected plan, or set direct=true.")
    trace.step(kind="validation", name="plan", ok=False,
               detail={"reason": FALLBACK_INVALID, "errors": reasons[:3]})
    return PlanOutcome(fallback_reason=FALLBACK_INVALID)
