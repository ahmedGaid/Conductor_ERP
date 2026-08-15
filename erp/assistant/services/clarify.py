"""Structured clarify (ai-reliability T5.10): a question that PAUSES the run instead of ending it.

Before this task a `clarify` decision was a dead end — the loop wrote the question as the turn's
answer, threw away everything it had gathered, and the user's reply started a brand-new run that
re-did the same lookups. Here a clarify with options becomes a card: the run parks
(``AgentRun.waiting_clarify``) with its plan and gathered results intact, and the user's pick — or
typed answer — resumes THE SAME run, with the answer appended to ``gathered`` as a
``user_answer`` result.

Everything in this module is a pure function over the model's raw JSON: no provider, no database,
no network. The parking/resume machinery that uses it lives in ``agent.py``; the prompt rules that
decide *when* to ask live in ``prompts/agent_loop.md``.
"""
from __future__ import annotations

# Options are a shortcut, not a menu: two is the smallest set worth rendering as buttons, and past
# four the card stops being a glance and becomes a form. A single option is not a choice — it
# degrades to a free-text question rather than pretending to offer one.
MIN_OPTIONS = 2
MAX_OPTIONS = 4

# Card labels are read at a glance, never scrolled.
MAX_LABEL_CHARS = 60
MAX_DESCRIPTION_CHARS = 120

# The synthetic result the user's answer becomes when the run resumes — a "tool" the planner reads
# exactly like any gathered result, so no prompt learns a second shape for the same thing.
USER_ANSWER_TOOL = "user_answer"


def _text(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def normalize_options(raw) -> list[dict]:
    """The model's proposed options as the card's own shape, or ``[]`` when they don't earn a card.

    Rules, in order: drop anything unusable (not an object, no label, duplicate label), keep at most
    ``MAX_OPTIONS``, keep at most ONE recommended (the first — a card that recommends everything
    recommends nothing), and require at least ``MIN_OPTIONS`` to survive. Fewer than that returns
    ``[]``, which is the free-text-only clarify: still a legal, useful question.
    """
    if not isinstance(raw, list):
        return []
    options: list[dict] = []
    seen: set[str] = set()
    recommended_taken = False
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = _text(item.get("label"), MAX_LABEL_CHARS)
        if not label or label.casefold() in seen:
            continue
        seen.add(label.casefold())
        option = {"label": label}
        description = _text(item.get("description"), MAX_DESCRIPTION_CHARS)
        if description:
            option["description"] = description
        if item.get("recommended") is True and not recommended_taken:
            option["recommended"] = True
            recommended_taken = True
        options.append(option)
        if len(options) == MAX_OPTIONS:
            break
    return options if len(options) >= MIN_OPTIONS else []


def build_card(decision: dict) -> dict | None:
    """The clarify card for one loop decision, or ``None`` when there is no question to ask.

    ``allow_free_text`` is always true: options are a shortcut past typing, never a cage — the
    composer stays open under every clarify card, so an answer nobody listed is always possible.
    """
    if not isinstance(decision, dict):
        return None
    question = str(decision.get("question") or "").strip()
    if not question:
        return None
    return {
        "question": question,
        "options": normalize_options(decision.get("options")),
        "allow_free_text": True,
        "status": "open",
    }


def parks(card: dict | None) -> bool:
    """Whether this clarify parks the run. Only an options card does: it is the one that gives the
    user something to click, so the answer comes back through the resume endpoint and lands on the
    same run. A free-text-only question is answered by typing in the composer — an ordinary next
    turn, exactly as it behaved before this task."""
    return bool(card and card.get("options"))


def answer_result(question: str, answer: str) -> dict:
    """The user's answer as a gathered result, so the resumed planner reads it as data rather than
    as a new request. Shaped like every other entry in ``results``: tool, why, data."""
    return {
        "tool": USER_ANSWER_TOOL,
        "why": _text(question, 200),
        "data": {"question": _text(question, 500), "answer": str(answer or "").strip()[:2000]},
    }
