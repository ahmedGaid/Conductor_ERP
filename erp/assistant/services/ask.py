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

from ..client import complete_stream
from ..tools import TOOLS, catalog_text
from . import context
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

# Appended after the context envelope (identity/user/page/company/persona) — the data-answering
# constraints that never change per request.
_ANSWER_TONE = (
    "Answer briefly and plainly, like a trusted colleague. Use ONLY the numbers and facts in DATA — "
    "never invent, estimate, or add figures that are not there. Money values in DATA are already "
    "formatted (e.g. '1,250.00 EGP') — quote them verbatim. When DATA is present it is already "
    "scoped to what this user is permitted to see (their branch/scope) — never claim a permission "
    "problem in that case. When DATA is empty because no matching report exists yet for this exact "
    "question, say plainly that Conductor cannot answer that specific question yet (not a "
    "permission issue) and suggest a nearby question you *can* answer. Only mention permissions "
    "when the question is about a module the user's role block says they cannot access. Never "
    "mention tools, JSON, schemas, or that you are an AI."
)


def _answer_system(actor, page: dict | None) -> str:
    return context.build_system_prompt(actor, page) + "\n\n" + _ANSWER_TONE

_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}

# Which router field feeds which tool argument.
_ARG_FIELDS = ("period", "query", "limit")


def answer_question(*, question: str, actor, conversation=None, page: dict | None = None) -> dict:
    """One question in → {answer, citations, used_tool} out. Read-only; audit-logged.

    When ``conversation`` is given the exchange is persisted: the user message is appended
    before the model runs, the assistant message (with citations/tool in ``meta``) after, and
    an empty conversation is auto-titled from the first question. Without it, behaviour is
    identical to before — the single-shot page keeps working. ``page`` is the optional client
    context envelope (current module/route/record) folded into the answer's system prompt.
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
        _answer_system(actor, page),
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


def _route_and_run(question: str, actor):
    """Shared front half of the pipeline: route → run the scoped tool → build citations.

    Returns ``(result, citations, used_tool)``. Same logic as ``answer_question`` up to the
    answer step, factored out so the streaming path can reuse it verbatim.
    """
    route = complete_json(_ROUTER_SYSTEM.format(catalog=catalog_text()), question, _ROUTER_SCHEMA)
    name = route.get("tool") or "none"
    tool = TOOLS.get(name)
    if tool is None:
        return {}, [], None
    kwargs = {k: route[k] for k in _ARG_FIELDS if route.get(k) is not None and k in tool.args}
    result = tool.run(actor, **kwargs)
    return result, tool.cite(result), name


def stream_answer(*, question: str, actor, conversation, page: dict | None = None):
    """Generator over the SSE chat pipeline — same route→run→answer as ``answer_question``, but the
    final answer streams token-by-token (plain prose, not JSON) so the UI renders as it arrives.

    Yields event dicts: ``{"type": "token"|"citations"|"done", ...}``. The user message is persisted
    before the model runs; the assistant message + audit land in a ``finally`` so a client
    disconnect mid-stream still saves whatever prose was produced (cancel costs nothing). Read-only.
    ``page`` is the optional client context envelope folded into the answer's system prompt.
    """
    q = (question or "").strip()[:MAX_QUESTION_CHARS]

    conversation.messages.create(role="user", content=q)
    if not conversation.title:
        conversation.title = q[:60]
    conversation.save()  # also touches updated_at

    result, citations, used = _route_and_run(q, actor)

    parts: list[str] = []
    saved = False

    def _persist():
        nonlocal saved
        if saved:
            return None
        saved = True
        answer = "".join(parts).strip()
        msg = conversation.messages.create(
            role="assistant", content=answer,
            meta={"citations": citations, "used_tool": used},
        )
        conversation.save()  # touch updated_at after the reply lands
        audit.record(
            module="assistant", action="ask", entity_type="Question", entity_id=used or "none",
            actor=actor, after={"tool": used, "citations": len(citations)},
        )
        return msg

    try:
        user = json.dumps({"question": q, "data": result}, ensure_ascii=False)
        for chunk in complete_stream([{"role": "user", "content": user}], system=_answer_system(actor, page)):
            parts.append(chunk)
            yield {"type": "token", "text": chunk}
        yield {"type": "citations", "citations": citations}
        msg = _persist()
        yield {"type": "done", "message_id": msg.id}
    finally:
        _persist()  # disconnect / error mid-stream still saves the partial answer
