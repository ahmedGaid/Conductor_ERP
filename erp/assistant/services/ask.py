"""Natural-language assistant over the user's *scoped* data (plan session 02, part 2).

Two constrained model calls, provider-portable (works identically on Anthropic / Gemini / Groq
because both use plain JSON mode — see ``llm.complete_json``):

1. **Route** — given the question and the tool catalog, the model picks ONE typed tool + its args.
   It never sees the ORM or SQL; it only chooses from a fixed list (DECISIONS: tool-use, not
   free-text-to-SQL).
2. **Answer** — we run that tool AS the current user (scope/RBAC/audit enforced), then hand the
   real, server-formatted result to the model to phrase in the user's language. Citations are built
   from the actual records in ``tools.py``, so links and numbers are never model-invented.

Every call is audit-logged. Writes are out of scope here — this endpoint only reads.
"""
from __future__ import annotations

import json

from erp.audit import services as audit

from ..tools import TOOLS, catalog_text
from .llm import complete_json

# Longest question we will send to the model — a cheap per-request guard (Part 3 cost control).
MAX_QUESTION_CHARS = 1000

_ROUTER_SYSTEM = (
    "You route a user's question to exactly ONE data tool for an Egyptian business ERP.\n"
    "Available tools:\n{catalog}\n"
    "Choose the single best tool and fill only the arguments it needs; leave the others null. "
    "If no tool fits (a greeting, or something these tools cannot answer), set tool to \"none\". "
    "Do not answer the question here or invent data — only choose the tool."
)

_ROUTER_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": [*TOOLS.keys(), "none"]},
        "period": {"type": ["string", "null"], "description": "this_month | last_month | this_year"},
        "query": {"type": ["string", "null"]},
        "limit": {"type": ["integer", "null"]},
    },
    "required": ["tool", "period", "query", "limit"],
    "additionalProperties": False,
}

_ANSWER_SYSTEM = (
    "You are المساعد الذكي, the assistant inside a calm Egyptian-Arabic ERP. Answer in the user's "
    "language (Arabic by default), briefly and plainly, like a trusted colleague. Use ONLY the "
    "numbers and facts in DATA — never invent, estimate, or add figures that are not there. Money "
    "values in DATA are already formatted (e.g. '1,250.00 EGP') — quote them verbatim. DATA is "
    "already limited to what this user is permitted to see (their branch and scope); if the question "
    "reaches beyond it, say plainly that you can only report on their own scope. Never mention tools, "
    "JSON, schemas, or that you are an AI."
)

_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}

# Which router field feeds which tool argument.
_ARG_FIELDS = ("period", "query", "limit")


def answer_question(*, question: str, actor, conversation=None) -> dict:
    """One question in → {answer, citations, used_tool} out. Read-only; audit-logged.

    When ``conversation`` is given the exchange is persisted: the user message is appended
    before the model runs, the assistant message (with citations/tool in ``meta``) after, and
    an empty conversation is auto-titled from the first question. Without it, behaviour is
    identical to before — the single-shot page keeps working.
    """
    q = (question or "").strip()[:MAX_QUESTION_CHARS]

    if conversation is not None:
        conversation.messages.create(role="user", content=q)
        if not conversation.title:
            conversation.title = q[:60]
        conversation.save()  # also touches updated_at

    route = complete_json(_ROUTER_SYSTEM.format(catalog=catalog_text()), q, _ROUTER_SCHEMA)
    name = route.get("tool") or "none"
    tool = TOOLS.get(name)

    if tool is None:
        # No data tool fits — let the model reply conversationally, but still bound to "only DATA"
        # (empty), so it explains what it can help with rather than inventing an answer.
        result, citations, used = {}, [], None
    else:
        kwargs = {k: route[k] for k in _ARG_FIELDS if route.get(k) is not None and k in tool.args}
        result = tool.run(actor, **kwargs)
        citations = tool.cite(result)
        used = name

    answer_obj = complete_json(
        _ANSWER_SYSTEM,
        json.dumps({"question": q, "data": result}, ensure_ascii=False),
        _ANSWER_SCHEMA,
    )
    answer = (answer_obj.get("answer") or "").strip()

    if conversation is not None:
        conversation.messages.create(
            role="assistant", content=answer,
            meta={"citations": citations, "used_tool": used},
        )
        conversation.save()  # touch updated_at after the reply lands

    audit.record(
        module="assistant", action="ask", entity_type="Question", entity_id=used or "none",
        actor=actor, after={"tool": used, "citations": len(citations)},
    )
    return {"answer": answer, "citations": citations, "used_tool": used}
