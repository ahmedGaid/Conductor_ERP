"""Rolling conversation summaries (ai-reliability T3.7): a thread beyond the envelope's raw-history
tail carries a maintained summary instead of silently losing its early turns to ``agent._recent_turns``'s
own cap (T3.6's degrade path shortens *what's fetched*, not what's remembered).

Fire-and-forget: ``maybe_trigger`` is called right after an assistant turn is persisted and never
blocks the response stream — a refresh (if due) runs as a Celery task, same mechanism as the
morning-digest tasks in ``tasks.py``. Fail-open like rerank (T3.5): a refresh that errors just
keeps the prior summary and tries again next turn, never breaks the chat itself.
"""
from __future__ import annotations

import json
import logging

from ..gateway.core import complete_json
from .prompt_registry import get as get_prompt
from .tracing import estimate_tokens

logger = logging.getLogger(__name__)

# The raw-history tail this many most-recent messages never gets summarized away — mirrors
# ``agent._HISTORY_TURNS`` (20 messages ≈ 10 turns), the same window ``_recent_turns`` fetches, so
# once ``summary_upto_message`` trails the latest message by this many, the summary is exactly what
# stands in for everything older. Kept as an independent constant (not imported from ``agent.py``)
# to avoid a circular import — ``agent.py`` imports this module, not the other way round.
TAIL_MESSAGES = 20

# Refresh at most this often: fewer than this many new (not-yet-summarized) older messages since
# the last refresh means the summary isn't stale enough yet to be worth another model call.
STALE_MESSAGE_GAP = 10

# Below this many estimated tokens of new older material, a refresh wouldn't save enough context
# budget to be worth its cost — matches the plan's "tokens(history beyond the last 10 turns) > 1500".
TOKEN_TRIGGER = 1500

_SCHEMA = {
    "type": "object", "required": ["summary"],
    "properties": {"summary": {"type": "string"}},
    "additionalProperties": False,
}


def _pending_older_messages(conversation) -> list:
    """Messages older than the tail, not yet folded into ``conversation.summary`` — oldest first."""
    messages = list(conversation.messages.order_by("id"))
    if len(messages) <= TAIL_MESSAGES:
        return []
    older = messages[:-TAIL_MESSAGES]
    upto_id = conversation.summary_upto_message_id
    if upto_id is None:
        return older
    return [m for m in older if m.id > upto_id]


def should_refresh(conversation) -> bool:
    """True when there's enough new, not-yet-summarized older material to justify one refresh call."""
    pending = _pending_older_messages(conversation)
    if len(pending) < STALE_MESSAGE_GAP:
        return False
    tokens = estimate_tokens(json.dumps(
        [{"role": m.role, "content": m.content} for m in pending], ensure_ascii=False))
    return tokens > TOKEN_TRIGGER


def refresh_summary(conversation) -> None:
    """Fold every pending older message into an updated summary, capped ~300 tokens by the prompt.

    Never raises: a provider/parse failure logs and leaves the prior summary standing exactly as
    it was — the next turn's trigger check tries again rather than the thread losing its summary.
    """
    pending = _pending_older_messages(conversation)
    if not pending:
        return
    prompt = get_prompt("thread_summary")
    turns_payload = [{"role": m.role, "content": m.content} for m in pending]
    system = prompt.render(
        prior_summary=conversation.summary or "(none yet)",
        turns=json.dumps(turns_payload, ensure_ascii=False),
    )
    try:
        result = complete_json(
            system, "Update the summary now.", _SCHEMA,
            feature="digest", conversation_id=conversation.id, prompt_ref=prompt.ref,
        )
        summary_text = (result.get("summary") or "").strip()
    except Exception:
        logger.exception("thread summary refresh failed for conversation %s — prior summary kept",
                         conversation.id)
        return
    if not summary_text:
        return
    conversation.summary = summary_text
    conversation.summary_upto_message = pending[-1]
    conversation.save(update_fields=["summary", "summary_upto_message", "updated_at"])


def maybe_trigger(conversation) -> None:
    """Enqueue a summary refresh iff due — call right after an assistant turn is persisted.
    Fire-and-forget: never awaited, never blocks the caller (matches the digest tasks' pattern)."""
    if not should_refresh(conversation):
        return
    from .. import tasks

    tasks.refresh_thread_summary.delay(conversation.id)
