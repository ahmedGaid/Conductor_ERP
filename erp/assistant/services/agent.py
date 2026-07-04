"""The agentic loop: understand → gather via tools → validate → answer (plan session 09).

The multi-round sibling of ``ask.py``'s single-shot router. Where ``ask`` picks one tool and
answers, the loop plans one step at a time: each round the model chooses to run a tool, ask one
clarifying question, or answer — so a question that spans several areas ("compare this month's sales
with purchases") is gathered across rounds and answered from the combined data.

Hard bounds keep it predictable and cheap:
- ``MAX_ROUNDS`` tool rounds, then it is forced to answer (never spins);
- read-only catalog only — the loop itself NEVER mutates (write proposals are session 10);
- every tool runs AS the actor, so RBAC/scope/audit hold. A tool permission error is information
  fed back to the model (an ``{"error": ...}`` result), not an exception — the model self-corrects.

Provider-portable: it reuses the same JSON seam (``complete_json``) and the same flat argument
schema as the router, plus the streaming seam (``complete_stream``) for the final prose. Tests
monkeypatch those two names on this module, exactly as they do for ``ask``.
"""
from __future__ import annotations

import json

from erp.audit import services as audit

from ..client import complete_stream
from ..query_registry import query_grammar_text
from ..tools import TOOLS, catalog_text
from . import context, files
from .ask import _ANSWER_TONE, _ARG_FIELDS, _ROUTER_SCHEMA, MAX_QUESTION_CHARS
from .llm import complete_json

# Most rounds a question ever needs; hit it and the loop is forced to answer with what it has.
MAX_ROUNDS = 6

# How much prior conversation the planner sees each round (keeps the prompt bounded).
_HISTORY_TURNS = 20

_LOOP_SYSTEM = (
    "You are the planning brain of an assistant for an Egyptian business ERP. Each round you decide "
    "the ONE next step toward fully answering the user, then stop and let the system run it.\n"
    "You have these read-only data tools, grouped by area:\n{catalog}\n"
    "The query_data tool is the flexible fallback for a count/total no specific tool covers. Its data "
    "sets and their allowed fields are:\n{query_grammar}\n"
    "For query_data set entity to a data set above and only use fields listed for it; put "
    "comparisons in filters as {{field, op, value}}, break-downs in group_by, and set aggregate "
    "(with metric for a sum/avg/min/max).\n"
    "Each round respond with EXACTLY ONE JSON object, one of:\n"
    '  {{"action": "tool", "tool": "<name>", "why": "<=8 words, shown to the user>", <args...>}}\n'
    '  {{"action": "clarify", "question": "<one short question>"}}\n'
    '  {{"action": "answer"}}\n'
    "Fill only the arguments the chosen tool needs; leave the rest null. Gather with as few tool "
    "calls as the question needs — you may call several tools across rounds to combine data from "
    "different areas. When you have enough to answer fully, choose answer. Choose clarify ONLY when "
    "the request is too vague to act on — never to stall. A tool result shaped {{\"error\": ...}} "
    "means that path is blocked or wrong: read it and try a different tool/arguments, or answer "
    "honestly — never repeat the same failing call. 'why' is a short human phrase like 'Checking "
    "this month's sales'. Never invent data; only these tools can see it."
)

# The planner's decision schema = the router's flat argument fields (proven across all three
# providers) plus the loop verbs. Keeping the arg fields flat avoids free-form-object schema quirks
# and lets the tool-arg mapping below reuse ``_ARG_FIELDS`` verbatim.
_LOOP_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["tool", "clarify", "answer"]},
        "why": {"type": ["string", "null"], "description": "<=8 words, shown to the user"},
        "question": {"type": ["string", "null"],
                     "description": "the clarifying question when action=clarify"},
        **_ROUTER_SCHEMA["properties"],
    },
    "required": ["action", "why", "question", *_ROUTER_SCHEMA["required"]],
    "additionalProperties": False,
}


def _answer_system(actor, page: dict | None) -> str:
    # Same envelope + data-answering constraints as the single-shot path; DATA now holds every
    # round's result rather than one.
    return context.build_system_prompt(actor, page) + "\n\n" + _ANSWER_TONE


def _recent_turns(conversation, exclude_id: int | None) -> list[dict]:
    """The last ~20 persisted turns (oldest first), minus the just-created user message, as plain
    role/content dicts for the planner prompt."""
    qs = conversation.messages.all()
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    tail = list(qs.order_by("-id")[:_HISTORY_TURNS])[::-1]
    return [{"role": m.role, "content": m.content} for m in tail]


def _loop_user(question: str, history: list[dict], results: list[dict], file_notes: list[str]) -> str:
    """The per-round planner input: prior turns, the current question, and everything gathered so
    far (each tool's why + result), so the model decides the next step in context."""
    payload = {
        "conversation_so_far": history,
        "question": question,
        "gathered": [{"tool": r["tool"], "why": r["why"], "result": r["data"]} for r in results],
    }
    if file_notes:
        payload["attached_files"] = file_notes
    return json.dumps(payload, ensure_ascii=False)


def _dedup(citations: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for c in citations:
        key = (c.get("type"), c.get("value"))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _run_tool(actor, decision: dict) -> tuple[dict, bool]:
    """Execute one planner tool decision as the actor. Returns ``(result, ok)``; any refusal, bad
    argument, or exception becomes an ``{"error": ...}`` result the model can read and correct —
    the loop never crashes on a tool call."""
    name = decision.get("tool") or "none"
    tool = TOOLS.get(name)
    if tool is None:
        return {"error": f"There is no tool named '{name}'. Choose one from the catalog."}, False
    kwargs = {k: decision[k] for k in _ARG_FIELDS if decision.get(k) is not None and k in tool.args}
    try:
        result = tool.run(actor, **kwargs)
    except Exception:  # bad argument shape etc. — feed a calm note back, don't tear down the loop
        return {"error": "That request could not be run. Try different arguments or another tool."}, False
    return result, "error" not in result


def run(*, actor, conversation, question: str, page: dict | None = None,
        regenerate: bool = False, attachment_ids=None):
    """Generator over the agentic chat pipeline — yields SSE-ready event dicts.

    Event protocol (extends session 02's token/citations/done/error):
      ``{"type": "step", "tool", "label", "state": "running"|"done", "ok"?}`` — one per tool call,
      ``{"type": "token", "text"}`` — final answer prose, streamed,
      ``{"type": "citations", "citations"}`` / ``{"type": "done", "message_id", "used_tool"}``.

    Persistence mirrors ``ask.stream_answer``: the user turn is saved before the model runs; the
    assistant turn (+ audit) lands in a ``finally`` so a client disconnect keeps the partial answer.
    ``regenerate`` re-answers the last question in place; ``attachment_ids`` are claimed onto the new
    user turn and folded into the model input (text files inline, images/PDF via the vision path).
    """
    # --- resolve the question + persist / clean up the user turn (mirrors stream_answer) ----------
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

    # Attached files: text/tabular fold into the planner input; images/PDF ride the vision path.
    media: list[dict] = []
    file_notes: list[str] = []
    if user_msg is not None:
        for att in user_msg.attachments.all():
            described = files.describe_for_model(att)
            if described.get("media"):
                media.append(described["media"])
            elif described.get("text"):
                file_notes.append(described["text"])

    history = _recent_turns(conversation, exclude_id=user_msg.id if user_msg else None)

    # --- the loop: plan → run a tool → repeat, until answer / clarify / round cap -----------------
    loop_system = _LOOP_SYSTEM.format(catalog=catalog_text(), query_grammar=query_grammar_text())
    results: list[dict] = []      # {tool, why, data} per executed tool
    steps: list[dict] = []        # {tool, why, ok} — persisted summaries, never raw payloads
    citations: list[dict] = []
    clarify_text: str | None = None

    for _round in range(MAX_ROUNDS):
        decision = complete_json(loop_system, _loop_user(q, history, results, file_notes), _LOOP_SCHEMA)
        action = decision.get("action")
        if action == "clarify":
            clarify_text = (decision.get("question") or "").strip()
            break
        if action != "tool":  # "answer", or anything unexpected → stop gathering and answer
            break
        name = decision.get("tool") or "none"
        why = (decision.get("why") or "").strip()
        yield {"type": "step", "tool": name, "label": why, "state": "running"}
        data, ok = _run_tool(actor, decision)
        results.append({"tool": name, "why": why, "data": data})
        steps.append({"tool": name, "why": why, "ok": ok})
        if ok:
            tool = TOOLS.get(name)
            citations.extend(tool.cite(data) if tool else [])
        yield {"type": "step", "tool": name, "label": why, "state": "done", "ok": ok}

    citations = _dedup(citations)
    # ``used_tool`` = the last tool that succeeded — keeps session-06's per-tool follow-up chips
    # working (client reads it from ``done`` and from the reloaded message meta).
    used_tool = next((s["tool"] for s in reversed(steps) if s["ok"]), None)

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
            meta={"citations": citations, "used_tool": used_tool, "steps": steps},
        )
        conversation.save()  # touch updated_at after the reply lands
        audit.record(
            module="assistant", action="ask", entity_type="Question", entity_id=used_tool or "none",
            actor=actor, after={"tools": [s["tool"] for s in steps], "citations": len(citations)},
        )
        return msg

    try:
        if clarify_text is not None:
            # A clarifying question IS the answer for this turn — no model stream, no citations.
            parts.append(clarify_text)
            citations = []
            yield {"type": "token", "text": clarify_text}
        else:
            user = json.dumps(
                {"question": q, "data": [{"tool": r["tool"], "result": r["data"]} for r in results]},
                ensure_ascii=False,
            )
            if file_notes:
                user += "\n\nAttached files:\n" + "\n\n".join(file_notes)
            for chunk in complete_stream(
                [{"role": "user", "content": user}], system=_answer_system(actor, page), media=media,
            ):
                parts.append(chunk)
                yield {"type": "token", "text": chunk}
        yield {"type": "citations", "citations": citations}
        msg = _persist()
        yield {"type": "done", "message_id": msg.id, "used_tool": used_tool}
    finally:
        _persist()  # disconnect / error mid-stream still saves the partial answer
