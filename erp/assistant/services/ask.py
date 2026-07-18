"""Natural-language assistant over the user's *scoped* data (plan session 02, part 2).

Two constrained model calls, provider-portable (works identically on Anthropic / Gemini / Groq
because both use plain JSON mode — see ``gateway.core.complete_json``):

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

from .. import client
from ..gateway import cache as semantic_cache
from ..gateway.core import complete_json, complete_stream
from ..query_registry import query_grammar_text
from ..tools import TOOLS, catalog_text
from . import context, files
from .prompt_registry import get as get_prompt

# Longest question we will send to the model — a cheap per-request guard (Part 3 cost control).
MAX_QUESTION_CHARS = 1000

_router_prompt = get_prompt("router")
_answer_tone_prompt = get_prompt("answer_tone")

_ROUTER_SYSTEM = _router_prompt.template

_ROUTER_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": [*TOOLS.keys(), "none"]},
        "period": {"type": ["string", "null"], "description": "this_month | last_month | this_year"},
        "query": {"type": ["string", "null"], "description": "free-text lookup (code, name, number)"},
        "limit": {"type": ["integer", "null"]},
        "status": {"type": ["string", "null"], "description": "an exact record status to filter by"},
        "supplier": {"type": ["string", "null"], "description": "supplier code or name to filter by"},
        "warehouse": {"type": ["string", "null"], "description": "warehouse code to limit to"},
        "days": {"type": ["integer", "null"], "description": "a day horizon (e.g. expiry window)"},
        "entity_type": {"type": ["string", "null"], "description": "a record type, e.g. SalesOrder"},
        "entity_id": {"type": ["string", "null"], "description": "a record id or number"},
        # query_data (the structured-query fallback) — a fixed grammar over the registry.
        "entity": {"type": ["string", "null"],
                   "description": "for query_data: the data set to list/count/total"},
        "filters": {
            "type": ["array", "null"],
            "description": "for query_data: conditions to narrow the rows",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "op": {"type": "string",
                           "description": "eq | gt | lt | gte | lte | contains | between"},
                    "value": {"type": "string", "description": "text value; for between: 'low,high'"},
                },
                "required": ["field", "op", "value"],
                "additionalProperties": False,
            },
        },
        "group_by": {"type": ["array", "null"], "items": {"type": "string"},
                     "description": "for query_data: 0–2 fields to break the total down by"},
        "aggregate": {"type": ["string", "null"],
                      "description": "for query_data: list | count | sum | avg | min | max"},
        "metric": {"type": ["string", "null"],
                   "description": "for query_data: the field to total for sum/avg/min/max"},
    },
    "required": ["tool", "period", "query", "limit", "status", "supplier", "warehouse", "days",
                 "entity_type", "entity_id", "entity", "filters", "group_by", "aggregate", "metric"],
    "additionalProperties": False,
}

# Appended after the context envelope (identity/user/page/company/persona) — the data-answering
# constraints that never change per request.
_ANSWER_TONE = _answer_tone_prompt.template


def _answer_system(actor, page: dict | None, question: str = "") -> str:
    # The language directive goes absolutely last — it is computed from the question, not inferred
    # by the model (see context.answer_language_directive).
    return "\n\n".join((
        context.build_system_prompt(actor, page),
        _ANSWER_TONE,
        context.answer_language_directive(question),
    ))


def _answer_prompt_ref() -> str:
    """The combined ref of every template in the answer system prompt (context envelope's
    static blocks + the closing answer-tone block) — shared by ask.py and agent.py since both
    build the same envelope + tone combination."""
    return f"{context.CONTEXT_PROMPT_REF}+{_answer_tone_prompt.ref}"

_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}

# Which router fields can feed a tool argument (each tool only receives the args it declares).
_ARG_FIELDS = ("period", "query", "limit", "status", "supplier", "warehouse", "days",
               "entity_type", "entity_id", "entity", "filters", "group_by", "aggregate", "metric")


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

    # T2.8: a near-duplicate of a previously-answered knowledge question skips the router + answer
    # model entirely — cheap, instant, scoped to this user at the current knowledge version.
    q_embedding = client.embed_text(
        q, actor=actor, conversation_id=conversation.id if conversation is not None else None)
    cached = semantic_cache.semantic_lookup(actor, q_embedding)

    if cached is not None:
        answer, citations, used, from_cache = cached["answer"], cached["citations"], "search_documents", True
    else:
        from_cache = False
        route = complete_json(
            _ROUTER_SYSTEM.format(catalog=catalog_text(), query_grammar=query_grammar_text()), q,
            _ROUTER_SCHEMA, feature="ask", actor=actor,
            conversation_id=conversation.id if conversation is not None else None,
            prompt_ref=_router_prompt.ref,
        )
        name = route.get("tool") or "none"
        tool = TOOLS.get(name)

        if tool is None:
            # No data tool fits — let the model reply conversationally, but still bound to "only
            # DATA" (empty), so it explains what it can help with rather than inventing an answer.
            result, citations, used = {}, [], None
        else:
            kwargs = {k: route[k] for k in _ARG_FIELDS if route.get(k) is not None and k in tool.args}
            result = tool.run(actor, **kwargs)
            citations = tool.cite(result)
            used = name

        answer_obj = complete_json(
            _answer_system(actor, page, q),
            json.dumps({"question": q, "data": result}, ensure_ascii=False),
            _ANSWER_SCHEMA, feature="ask", actor=actor,
            conversation_id=conversation.id if conversation is not None else None,
            prompt_ref=_answer_prompt_ref(),
        )
        answer = (answer_obj.get("answer") or "").strip()

        if used == "search_documents" and answer:
            semantic_cache.semantic_put(
                actor, question_text=q, embedding=q_embedding, answer=answer, citations=citations,
            )

    if conversation is not None:
        conversation.messages.create(
            role="assistant", content=answer,
            meta={"citations": citations, "used_tool": used, "from_cache": from_cache},
        )
        conversation.save()  # touch updated_at after the reply lands

    audit.record(
        module="assistant", action="ask", entity_type="Question", entity_id=used or "none",
        actor=actor, after={"tool": used, "citations": len(citations), "from_cache": from_cache},
    )
    return {"answer": answer, "citations": citations, "used_tool": used, "from_cache": from_cache}


def _route_and_run(question: str, actor, conversation_id=None):
    """Shared front half of the pipeline: route → run the scoped tool → build citations.

    Returns ``(result, citations, used_tool)``. Same logic as ``answer_question`` up to the
    answer step, factored out so the streaming path can reuse it verbatim.
    """
    route = complete_json(
        _ROUTER_SYSTEM.format(catalog=catalog_text(), query_grammar=query_grammar_text()),
        question, _ROUTER_SCHEMA, feature="ask", actor=actor, conversation_id=conversation_id,
        prompt_ref=_router_prompt.ref,
    )
    name = route.get("tool") or "none"
    tool = TOOLS.get(name)
    if tool is None:
        return {}, [], None
    kwargs = {k: route[k] for k in _ARG_FIELDS if route.get(k) is not None and k in tool.args}
    result = tool.run(actor, **kwargs)
    return result, tool.cite(result), name


def stream_answer(*, question: str, actor, conversation, page: dict | None = None,
                  regenerate: bool = False, attachment_ids=None):
    """Generator over the SSE chat pipeline — same route→run→answer as ``answer_question``, but the
    final answer streams token-by-token (plain prose, not JSON) so the UI renders as it arrives.

    Yields event dicts: ``{"type": "token"|"citations"|"done", ...}``. The user message is persisted
    before the model runs; the assistant message + audit land in a ``finally`` so a client
    disconnect mid-stream still saves whatever prose was produced (cancel costs nothing). Read-only.
    ``page`` is the optional client context envelope folded into the answer's system prompt.

    ``regenerate`` re-answers the conversation's last user message without adding a new user turn:
    any assistant message after it (the previous answer, or an empty one left by an error) is dropped
    first, so retry/regenerate never duplicate the question. The view guarantees a prior user message.

    ``attachment_ids`` are claimed onto the new user message; each file's ``describe_for_model``
    output rides along to the model — tabular/text files as extra question text, images/PDF via the
    vision path. On regenerate the last message's own attachments are re-fed, so it stays faithful.
    """
    if regenerate:
        user_msg = conversation.messages.filter(role="user").last()
        q = (user_msg.content if user_msg else "").strip()[:MAX_QUESTION_CHARS]
        if user_msg is not None:
            conversation.messages.filter(role="assistant", id__gt=user_msg.id).delete()
    else:
        q = (question or "").strip()[:MAX_QUESTION_CHARS]
        user_msg = conversation.messages.create(role="user", content=q)
        if attachment_ids:
            claimed = files.claim_attachments(attachment_ids, user=actor, message=user_msg)
            user_msg.meta = {"attachments": files.attachment_chips(claimed)}
            user_msg.save(update_fields=["meta"])
        if not conversation.title:
            conversation.title = q[:60]
        conversation.save()  # also touches updated_at

    # Fold any attached files into the model call: text tables/dumps extend the question, images/PDF
    # go to the provider's vision path.
    media: list[dict] = []
    file_notes: list[str] = []
    if user_msg is not None:
        for att in user_msg.attachments.all():
            described = files.describe_for_model(att)
            if described.get("media"):
                media.append(described["media"])
            elif described.get("text"):
                file_notes.append(described["text"])

    result, citations, used = _route_and_run(q, actor, conversation_id=conversation.id)

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
        if file_notes:
            user += "\n\nAttached files:\n" + "\n\n".join(file_notes)
        for chunk in complete_stream(
            [{"role": "user", "content": user}], system=_answer_system(actor, page, q), media=media,
            feature="chat", actor=actor, conversation_id=conversation.id,
            prompt_ref=_answer_prompt_ref(),
        ):
            parts.append(chunk)
            yield {"type": "token", "text": chunk}
        yield {"type": "citations", "citations": citations}
        msg = _persist()
        # ``used_tool`` lets the client offer curated follow-up questions for that tool (session 06).
        yield {"type": "done", "message_id": msg.id, "used_tool": used}
    finally:
        _persist()  # disconnect / error mid-stream still saves the partial answer
