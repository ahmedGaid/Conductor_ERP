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
import time

from django.conf import settings

from erp.audit import services as audit

from ..gateway.core import complete_json, complete_stream, model_id, provider
from ..models import AgentRun, AgentStep
from ..query_registry import REGISTRY as _QUERY_REGISTRY
from ..query_registry import query_grammar_text
from ..tools import TOOLS, catalog_text
from . import actions, context, envelope, files, imports, suggestions, summarize
from .ask import _ANSWER_TONE, _ARG_FIELDS, _ROUTER_SCHEMA, MAX_QUESTION_CHARS, _answer_prompt_ref
from .prompt_registry import get as get_prompt
from .tracing import NULL_HANDLE, estimate_tokens, mark_cancelled, trace_call

# Most rounds a question ever needs; hit it and the loop is forced to answer with what it has.
MAX_ROUNDS = 6

# How much prior conversation a round's DB query fetches (envelope.assemble decides how much of
# that actually enters the prompt — see ``_degrade_list_half``); a generous fetch ceiling here is
# just a cheap upper bound on the query, not the token-budget control itself (T3.6).
_HISTORY_TURNS = 20

_loop_prompt = get_prompt("agent_loop")

_LOOP_SYSTEM = _loop_prompt.template

# The planner's decision schema = the router's flat argument fields (proven across all three
# providers) plus the loop verbs. Keeping the arg fields flat avoids free-form-object schema quirks
# and lets the tool-arg mapping below reuse ``_ARG_FIELDS`` verbatim.
# Action arguments the planner may fill for a "propose" decision. Flat, like the tool args: scalar
# fields reuse the router schema (supplier/warehouse/query); only the action-specific ones are new.
_ACTION_FIELDS = {
    "name": {"type": ["string", "null"], "description": "the action name when action=propose"},
    "target": {"type": ["string", "null"],
               "description": "when action=import: the list the file holds — "
                              "customers | suppliers | items (leave null to let the system detect)"},
    "customer": {"type": ["string", "null"], "description": "customer code or name (sales order)"},
    "from_low_stock": {"type": ["boolean", "null"],
                       "description": "true to fill a purchase request from low-stock items"},
    "items": {
        "type": ["array", "null"],
        "description": "line items to create: item (sku or name), quantity, optional unit_cost (minor)",
        "items": {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "quantity": {"type": "string"},
                "unit_cost": {"type": ["integer", "null"]},
            },
            "required": ["item", "quantity", "unit_cost"],
            "additionalProperties": False,
        },
    },
}

_LOOP_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string",
                   "enum": ["tool", "propose", "import", "clarify", "suggest", "answer"]},
        "why": {"type": ["string", "null"], "description": "<=8 words, shown to the user"},
        "question": {"type": ["string", "null"],
                     "description": "the clarifying question when action=clarify"},
        "resume": {"type": ["string", "null"],
                   "description": "when action=suggest: one sentence — what you will continue "
                                  "after the user fixes the blocker"},
        "intent": {"type": ["string", "null"],
                   "description": "on your FIRST decision only: the request's intent, one of "
                                  "lookup | report | document_search | create | update | "
                                  "workflow | file | explain | conversation | mixed"},
        **_ROUTER_SCHEMA["properties"],
        **_ACTION_FIELDS,
    },
    "required": ["action", "why", "question", "resume", "intent", *_ROUTER_SCHEMA["required"],
                 *_ACTION_FIELDS.keys()],
    "additionalProperties": False,
}


def _answer_system(actor, page: dict | None, conversation=None, question: str = "",
                   *, model: str | None = None) -> tuple[str, dict]:
    # Same envelope + data-answering constraints as the single-shot path; DATA now holds every
    # round's result rather than one. The computed reply-language directive closes it, as in ask.
    # Returns the composition record alongside the string (T3.6) — the answer tone + language
    # directive are small fixed blocks, always included, not worth their own envelope section.
    prompt, meta = context.build_system_prompt_with_meta(actor, page, conversation, model=model,
                                                         message=question)
    return "\n\n".join((prompt, _ANSWER_TONE, context.answer_language_directive(question))), meta


def _degrade_list_half(content: str) -> str | None:
    """Drop the OLDEST half of a JSON array, keeping the most recent entries — shared by the
    planner's per-round history/gathered sections and the final answer's results payload (T3.6).
    Older turns and earlier tool calls are the least likely to matter to the current step; a
    single shared policy means history and tool-results never drift onto different degrade rules."""
    try:
        items = json.loads(content)
    except ValueError:
        return None
    if not isinstance(items, list) or len(items) <= 1:
        return None
    return json.dumps(items[len(items) // 2:], ensure_ascii=False)


def _any_compacted(*metas: dict) -> bool:
    return any(v.get("trimmed") or v.get("dropped") for m in metas for v in m.values())


def _last_user_text(conversation) -> str:
    """The most recent thing the user typed — the language signal for turns we generate ourselves."""
    if conversation is None:
        return ""
    message = conversation.messages.filter(role="user").order_by("-created_at").first()
    return message.content if message else ""


def _recent_turns(conversation, exclude_id: int | None) -> list[dict]:
    """The last ~20 persisted turns (oldest first), minus the just-created user message, as plain
    role/content dicts for the planner prompt.

    T3.7: once the conversation has a rolling summary, turns it already covers are excluded here —
    they're represented by the summary section instead (see ``_loop_user``), never duplicated into
    raw history. ``summarize.TAIL_MESSAGES`` mirrors this same window, so once the summary is kept
    fresh the two caps agree and this filter is a no-op beyond what the slice below already does."""
    qs = conversation.messages.all()
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    if conversation.summary_upto_message_id is not None:
        qs = qs.filter(id__gt=conversation.summary_upto_message_id)
    tail = list(qs.order_by("-id")[:_HISTORY_TURNS])[::-1]
    return [{"role": m.role, "content": m.content} for m in tail]


def _recent_vision_attachments(conversation, exclude_id: int | None) -> list:
    """The image/PDF attachments of the most recent EARLIER turn that carried any (within the history
    window). Used to keep an attached image in view across follow-up turns: it is claimed onto the one
    message that first referenced it, so 'ok, create that invoice' / 'take the items from the image' —
    sent as fresh messages with no attachment of their own — would otherwise leave the planner blind.
    Vision only (image/PDF): tabular files route through their own import card, so they are not
    carried forward."""
    qs = conversation.messages.filter(role="user")
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    for m in qs.order_by("-id")[:_HISTORY_TURNS]:
        atts = [a for a in m.attachments.all()
                if (a.content_type or "").lower() in files.VISION_TYPES]
        if atts:
            return atts
    return []


def _loop_user(question: str, history: list[dict], results: list[dict], file_notes: list[str],
               *, model: str, max_tokens: int, summary: str = "") -> tuple[str, dict]:
    """The per-round planner input: prior turns, the current question, and everything gathered so
    far (each tool's why + result), so the model decides the next step in context.

    ``history`` and ``gathered`` grow every round (more tool results) and every conversation turn
    (more history) — exactly the multi-round accumulation T3.6 exists to bound. Both go through the
    envelope manager as their own sections (``gathered`` kept at higher priority: the data this
    round actually needs beats older conversation) instead of the old hard ``_HISTORY_TURNS`` cap.

    T3.7: when the conversation has a maintained summary, it rides as its own section — priority
    just above ``history`` — so turns older than the raw-history tail are represented by the
    summary instead of being dropped outright once the envelope runs short of budget.
    """
    gathered = [{"tool": r["tool"], "why": r["why"], "result": r["data"]} for r in results]
    sections = [
        envelope.Section("gathered", 0, json.dumps(gathered, ensure_ascii=False),
                         max_share=0.7, degrade_fn=_degrade_list_half),
    ]
    if summary:
        sections.append(envelope.Section("summary", 1, summary))
    sections.append(envelope.Section("history", 2, json.dumps(history, ensure_ascii=False),
                                     max_share=0.4, degrade_fn=_degrade_list_half))
    kept, meta = envelope.assemble(sections, model=model, max_tokens=max_tokens)
    payload = {
        "conversation_so_far": json.loads(kept.get("history", "[]")),
        "question": question,
        "gathered": json.loads(kept.get("gathered", "[]")),
    }
    if "summary" in kept:
        payload["earlier_conversation_summary"] = kept["summary"]
    if file_notes:
        payload["attached_files"] = file_notes
    return json.dumps(payload, ensure_ascii=False), meta


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


def _run_tool(actor, decision: dict, *, trace=None) -> tuple[dict, bool]:
    """Execute one planner tool decision as the actor. Returns ``(result, ok)``; any refusal, bad
    argument, or exception becomes an ``{"error": ...}`` result the model can read and correct —
    the loop never crashes on a tool call. ``trace`` (the run's handle) is passed to every tool as
    the reserved ``_trace`` kwarg — swallowed by each tool's ``**_`` except search_documents, which
    uses it to record a T3.2 retrieval step."""
    name = decision.get("tool") or "none"
    tool = TOOLS.get(name)
    if tool is None:
        return {"error": f"There is no tool named '{name}'. Choose one from the catalog."}, False
    kwargs = {k: decision[k] for k in _ARG_FIELDS if decision.get(k) is not None and k in tool.args}
    try:
        result = tool.run(actor, _trace=trace, **kwargs)
    except Exception:  # bad argument shape etc. — feed a calm note back, don't tear down the loop
        return {"error": "That request could not be run. Try different arguments or another tool."}, False
    return result, "error" not in result


def _step_args(decision: dict) -> dict:
    """The scalar args a round decided on — never the full tool result (Trace/TraceStep policy)."""
    return {k: decision[k] for k in _ARG_FIELDS if decision.get(k) is not None}


def _step_start(agent_run: AgentRun | None, seq: int, tool: str, decision: dict) -> AgentStep | None:
    """Write-ahead: persist the step BEFORE the tool call it describes runs, so a crash mid-call
    leaves a ``running`` row (never a silent gap) — the caller's own except turns it ``failed``."""
    if agent_run is None:
        return None
    step = AgentStep.objects.create(run=agent_run, seq=seq, tool=tool, args=_step_args(decision),
                                    status=AgentStep.Status.PENDING)
    AgentStep.objects.filter(pk=step.pk).update(status=AgentStep.Status.RUNNING)
    AgentRun.objects.filter(pk=agent_run.pk).update(current_step=seq)
    return step


def _step_finish(step: AgentStep | None, *, ok: bool, data: dict) -> None:
    if step is None:
        return
    status = AgentStep.Status.OK if ok else AgentStep.Status.FAILED
    error = "" if ok else str((data or {}).get("error") or (data or {}).get("blocker") or "")[:255]
    AgentStep.objects.filter(pk=step.pk).update(
        status=status, error=error,
        result_summary={"result_size": len(json.dumps(data, ensure_ascii=False))},
    )


def _fail_lingering_steps(agent_run: AgentRun | None, error_class: str) -> None:
    """A run that ends by exception or cancellation before a step's own finish call — any step
    still ``pending``/``running`` gets an honest terminal row instead of hanging forever."""
    if agent_run is None:
        return
    AgentStep.objects.filter(
        run=agent_run, status__in=[AgentStep.Status.PENDING, AgentStep.Status.RUNNING],
    ).update(status=AgentStep.Status.FAILED, error=error_class[:255])


def run(*, actor, conversation, question: str, page: dict | None = None,
        regenerate: bool = False, attachment_ids=None, stream_id=None):
    """Same as ``_run_impl`` — opens one Trace for the whole agent run (planner rounds + tool
    calls as TraceSteps) and closes it however the run ends: answered, hit MAX_ROUNDS, raised, or
    the client disconnected mid-stream (``Trace.meta.stop``). Also opens the durable ``AgentRun``
    row (T5.1) alongside the Trace — same three exits, so both always land in a matching terminal
    state.

    ``stream_id`` (T5.9): when set, the run is a detached worker turn — the assistant reply
    checkpoints into one deterministic ``Message`` row (keyed by this id) instead of only being
    created at the very end, so a job retry upserts rather than duplicates. ``None`` (default) is
    the unchanged in-request path: no checkpoint row, no new event type, identical behavior."""
    cm = trace_call("agent", actor=actor, conversation_id=getattr(conversation, "id", None),
                    prompt_ref=_loop_prompt.ref)
    handle = cm.__enter__()
    agent_run = AgentRun.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        conversation=conversation, goal=(question or "")[:MAX_QUESTION_CHARS],
    )
    try:
        yield from _run_impl(actor=actor, conversation=conversation, question=question, page=page,
                             regenerate=regenerate, attachment_ids=attachment_ids, trace=handle,
                             agent_run=agent_run, stream_id=stream_id)
    except GeneratorExit:
        handle.meta["stop"] = "cancelled"
        mark_cancelled(handle)
        cm.__exit__(None, None, None)
        _fail_lingering_steps(agent_run, "cancelled")
        AgentRun.objects.filter(pk=agent_run.pk).update(
            status=AgentRun.Status.CANCELLED, trace_id=handle.trace_id or None)
        raise
    except BaseException as exc:
        handle.meta.setdefault("stop", "error")
        cm.__exit__(type(exc), exc, exc.__traceback__)
        _fail_lingering_steps(agent_run, exc.__class__.__name__)
        AgentRun.objects.filter(pk=agent_run.pk).update(
            status=AgentRun.Status.FAILED, trace_id=handle.trace_id or None)
        raise
    else:
        cm.__exit__(None, None, None)
        AgentRun.objects.filter(pk=agent_run.pk).update(
            status=AgentRun.Status.DONE, trace_id=handle.trace_id or None)


def _run_impl(*, actor, conversation, question: str, page: dict | None = None,
              regenerate: bool = False, attachment_ids=None, trace=NULL_HANDLE,
              agent_run: AgentRun | None = None, stream_id=None):
    """Generator over the agentic chat pipeline — yields SSE-ready event dicts.

    Event protocol (extends session 02's token/citations/done/error):
      ``{"type": "step", "tool", "label", "state": "running"|"done", "ok"?}`` — one per tool call,
      ``{"type": "token", "text"}`` — final answer prose, streamed,
      ``{"type": "citations", "citations"}`` / ``{"type": "done", "message_id", "used_tool"}``.

    Persistence mirrors ``ask.stream_answer``: the user turn is saved before the model runs; the
    assistant turn (+ audit) lands in a ``finally`` so a client disconnect keeps the partial answer.
    ``regenerate`` re-answers the last question in place; ``attachment_ids`` are claimed onto the new
    user turn and folded into the model input (text files inline, images/PDF via the vision path).
    ``trace`` (default a no-op handle) records this run's steps — see the ``run()`` wrapper above.
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

    # T5.9: a detached worker turn checkpoints into one deterministic row — created AFTER the
    # regenerate cleanup above (which deletes assistant rows past the last user message) so a
    # retry's stale partial from the interrupted attempt is gone before this one is created, and
    # ``get_or_create`` makes a redelivered task (Celery ACKS_LATE) upsert instead of duplicate.
    checkpoint_message = None
    if stream_id is not None:
        # ``meta.streaming`` is how the client tells this placeholder row apart from a settled
        # answer on reload — a live worker is still writing it, so it isn't safe to treat as final
        # yet. The eventual ``_persist()`` write below replaces ``meta`` wholesale, dropping the
        # flag the moment the turn actually settles.
        checkpoint_message, _ = conversation.messages.get_or_create(
            stream_id=stream_id, defaults={"role": "assistant", "content": "", "meta": {"streaming": True}},
        )
        yield {"type": "checkpoint", "message_id": checkpoint_message.id}

    # Attached files: text/tabular fold into the planner input as text; images/PDF ride the vision
    # path — handed to BOTH the planner (so it can read them to fill a propose) and the final answer.
    media: list[dict] = []
    file_notes: list[str] = []
    if user_msg is not None:
        for att in user_msg.attachments.all():
            described = files.describe_for_model(att)
            if described.get("media"):
                media.append(described["media"])
                # A text breadcrumb so the planner's prompt also names the attachment — the image
                # itself is injected alongside, so it reads the values rather than asking for them.
                file_notes.append(
                    f"[attached image/PDF '{att.name}' is provided to you directly — read it for any "
                    "values the user points to; extract supplier and line items to propose a record]"
                )
            elif described.get("text"):
                file_notes.append(described["text"])

    # Carry an earlier image/PDF forward when THIS turn attached none of its own — so a follow-up
    # that refers to "the attached image" ('ok, create that invoice', 'take the items from it') keeps
    # the attachment in the planner's eyes instead of going blind. Only when the current turn has no
    # vision media; the file is read fresh each such turn (bounded to one prior image-bearing turn).
    if not media and user_msg is not None:
        for att in _recent_vision_attachments(conversation, exclude_id=user_msg.id):
            described = files.describe_for_model(att)
            if described.get("media"):
                media.append(described["media"])
                file_notes.append(
                    f"[image/PDF '{att.name}' attached earlier in this conversation is still provided "
                    "to you directly — read it for any values the user refers to; extract supplier and "
                    "line items to propose a record. Do not ask the user to retype what it shows]"
                )

    history = _recent_turns(conversation, exclude_id=user_msg.id if user_msg else None)
    thread_summary = conversation.summary if conversation is not None else ""

    # --- the loop: plan → run a tool → repeat, until answer / clarify / round cap -----------------
    loop_system = _loop_prompt.render(catalog=catalog_text(), query_grammar=query_grammar_text(),
                                      action_catalog=actions.catalog_text())
    # Page-record resolution (session 11): when the user is ON a record page (and hasn't detached
    # it), pronouns and bare references resolve to that record — the planner reaches for the
    # matching detail tool with the record's identifier instead of asking "which order?".
    record = (page or {}).get("record") or {}
    if record.get("label") and not (page or {}).get("detached"):
        loop_system = (
            f"The user is currently viewing {record.get('type', 'record')} "
            f"{record.get('id', '')} ({record['label']}). Pronouns and bare references "
            "('this order', 'هذا الأمر', 'it', 'the customer', 'هذا العميل') resolve to this "
            "page record — never ask which record is meant. Prefer tools scoped to it, passing "
            f"its number or name ('{record['label']}') as the query.\n\n"
        ) + loop_system
    # The planner writes user-facing prose too — the `clarify` question never passes through the
    # answer path, so it needs the same computed language rule or an Arabic question can come back
    # with an English "which order did you mean?" (caught by refusal_ar_08).
    loop_system += "\n\n" + context.answer_language_directive(q)
    results: list[dict] = []      # {tool, why, data} per executed tool
    steps: list[dict] = []        # {tool, why, ok} — persisted summaries, never raw payloads
    citations: list[dict] = []
    clarify_text: str | None = None
    proposal: dict | None = None  # a built write proposal (session 10) — the turn ends after one
    import_task: dict | None = None  # a spreadsheet import card (session 14) — ends the turn too
    suggestion: dict | None = None  # a blocker turned actionable (session 12) — ends the turn too
    pending: dict | None = None     # the blocked decision, kept in meta for session 13's resume
    last_blocker: dict | None = None
    last_decision: dict | None = None  # the round that ended the loop — the grounding guard reads it
    intent: str | None = None
    seen_calls: set[tuple] = set()
    total_in_tokens = 0
    total_out_tokens = 0
    hit_round_cap = False
    # T3.6: one budget for the whole run — the primary provider's model and the reply ceiling never
    # change mid-turn, so this is computed once rather than re-resolved every round.
    model = model_id()
    max_tokens = settings.ASSISTANT_MAX_TOKENS
    loop_envelope_meta: dict = {}

    for _round in range(MAX_ROUNDS):
        # media rides every round: the planner keeps its eyes on the attachment until it proposes
        # (usually round 1), so it can read supplier/lines from an image instead of guessing them.
        round_user, loop_envelope_meta = _loop_user(
            q, history, results, file_notes, model=model, max_tokens=max_tokens,
            summary=thread_summary)
        _t0 = time.monotonic()
        decision = complete_json(loop_system, round_user, _LOOP_SCHEMA, media=media)
        trace.step(kind="llm", name=f"round{_round + 1}", ok=True,
                  latency_ms=int((time.monotonic() - _t0) * 1000),
                  detail={"prompt_ref": _loop_prompt.ref})
        total_in_tokens += estimate_tokens(loop_system + round_user)
        total_out_tokens += estimate_tokens(json.dumps(decision, ensure_ascii=False))
        last_decision = decision
        if intent is None:
            intent = decision.get("intent")
        action = decision.get("action")
        if action == "clarify":
            clarify_text = (decision.get("question") or "").strip()
            break
        if action == "propose":
            # The model proposes a write; we build it (validate + price, no write) and end the turn.
            # A refusal/unresolved build is fed back as data so the answer explains it calmly — no card.
            pname = decision.get("name") or ""
            built = actions.build(actor, pname, decision)
            results.append({"tool": f"propose:{pname}", "why": (decision.get("why") or "").strip(),
                            "data": built})
            if "blocker" in built:
                # A dependency the write leans on is missing/inactive/ambiguous — don't end the
                # turn: keep the blocked decision and loop so the model's next step is "suggest".
                last_blocker = built["blocker"]
                pending = {k: v for k, v in decision.items()
                           if v is not None and k not in ("action", "why", "intent", "resume")}
                continue
            if "error" not in built:
                proposal = built
            break
        if action == "import":
            # A bulk import from an attached spreadsheet: find the tabular attachment on this turn,
            # inspect it (map columns → fields), and end the turn with a mapping-stage card. The
            # planner never sees the attachment id — the file is resolved server-side from the user
            # turn, so it can't point the import at another file.
            tabular = next(
                (a for a in (user_msg.attachments.all() if user_msg else [])
                 if (a.content_type or "").lower() in files.IMPORT_TYPES),
                None,
            )
            why = (decision.get("why") or "").strip()
            if tabular is None:
                results.append({"tool": "import", "why": why, "data": {
                    "error": "No spreadsheet is attached to import. Ask the user to attach a CSV or "
                             "Excel file of the customers, suppliers, or items to add."}})
                break
            inspected = imports.inspect(actor, tabular, decision.get("target"))
            results.append({"tool": "import", "why": why, "data": inspected})
            if "error" not in inspected:
                import_task = imports.as_card(inspected, tabular.id)
            break
        if action == "suggest":
            # Blocker → actionable card: issue + the actor's permitted fixes + the resume promise.
            # Without a stored blocker there is nothing to suggest — fall through to answer.
            if last_blocker is not None:
                suggestion = suggestions.build_suggestion(
                    actor, last_blocker, (decision.get("resume") or "").strip())
            break
        if action != "tool":  # "answer", or anything unexpected → stop gathering and answer
            break
        name = decision.get("tool") or "none"
        why = (decision.get("why") or "").strip()
        signature = (name, tuple(sorted(
            (k, str(decision.get(k))) for k in _ARG_FIELDS if decision.get(k) is not None
        )))
        if signature in seen_calls:
            trace.step(kind="validation", name=name, ok=False, detail={"reason": "duplicate_call"})
            results.append({"tool": name, "why": why, "data": {
                "error": "You already ran this exact call this turn. Use its earlier result, "
                         "change the arguments, or answer."}})
            continue
        seen_calls.add(signature)
        step_row = _step_start(agent_run, len(steps) + 1, name, decision)
        yield {"type": "step", "tool": name, "label": why, "state": "running"}
        _t0 = time.monotonic()
        data, ok = _run_tool(actor, decision, trace=trace)
        blocked = isinstance(data, dict) and "blocker" in data
        _step_finish(step_row, ok=ok and not blocked, data=data)
        trace.step(kind="tool", name=name, ok=ok and not blocked,
                  latency_ms=int((time.monotonic() - _t0) * 1000),
                  detail={"result_size": len(json.dumps(data, ensure_ascii=False))})
        if blocked:  # no tool emits blockers today, but the convention is tool-wide (Task A)
            last_blocker = data["blocker"]
        results.append({"tool": name, "why": why, "data": data})
        steps.append({"tool": name, "why": why, "ok": ok and not blocked})
        if ok and not blocked:
            tool = TOOLS.get(name)
            citations.extend(tool.cite(data) if tool else [])
        yield {"type": "step", "tool": name, "label": why, "state": "done", "ok": ok and not blocked}
    else:
        hit_round_cap = True

    # Deterministic grounding guard (2026-07-04, rag-knowledge FILE_11 follow-up): the planner
    # sometimes classifies a question as document-shaped (intent) yet reaches answer without ever
    # calling search_documents — reproduced live both as a false "no document found" and, worse,
    # as an invented document name/content. Prompt wording alone has been hardened twice already
    # with no durable effect (see DECISIONS.md), so force one real search here rather than trust
    # the model to remember. This only fires for document-shaped intents and only once.
    if (clarify_text is None and proposal is None and intent in ("document_search", "mixed")
            and not any(r["tool"] == "search_documents" for r in results)):
        name = "search_documents"
        why = "Checking company documents"
        guard_decision = {"tool": name, "query": q}
        step_row = _step_start(agent_run, len(steps) + 1, name, guard_decision)
        yield {"type": "step", "tool": name, "label": why, "state": "running"}
        _t0 = time.monotonic()
        data, ok = _run_tool(actor, guard_decision, trace=trace)
        _step_finish(step_row, ok=ok, data=data)
        trace.step(kind="tool", name=name, ok=ok, latency_ms=int((time.monotonic() - _t0) * 1000),
                  detail={"result_size": len(json.dumps(data, ensure_ascii=False))})
        results.append({"tool": name, "why": why, "data": data})
        steps.append({"tool": name, "why": why, "ok": ok})
        if ok:
            tool = TOOLS.get(name)
            citations.extend(tool.cite(data) if tool else [])
        yield {"type": "step", "tool": name, "label": why, "state": "done", "ok": ok}

    # Live-data grounding guard (query-data-list-mode plan, 2026-07-07): the same failure the
    # document guard closes, on the data side — a lookup/report intent answered with zero
    # successful tool calls is a fabrication risk. There is no safe way to guess which of ~20 data
    # tools the user meant, so this fires only when the planner itself NAMED a query_data entity
    # yet answered anyway: run that query for real before the answer streams. The fully-unnamed
    # case (no entity anywhere) stays open — see the erp-status backlog entry.
    guard_entity = ((last_decision or {}).get("entity") or "").strip()
    if (clarify_text is None and proposal is None and suggestion is None
            and intent in ("lookup", "report")
            and not any(s["ok"] for s in steps)
            and not any(r["tool"] == "query_data" for r in results)
            and guard_entity in _QUERY_REGISTRY):
        name = "query_data"
        why = "Checking the live data"
        guard_decision = {**last_decision, "tool": name}
        step_row = _step_start(agent_run, len(steps) + 1, name, guard_decision)
        yield {"type": "step", "tool": name, "label": why, "state": "running"}
        _t0 = time.monotonic()
        data, ok = _run_tool(actor, guard_decision, trace=trace)
        _step_finish(step_row, ok=ok, data=data)
        trace.step(kind="tool", name=name, ok=ok, latency_ms=int((time.monotonic() - _t0) * 1000),
                  detail={"result_size": len(json.dumps(data, ensure_ascii=False))})
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
    trace.meta["stop"] = "step_budget" if hit_round_cap else "answered"
    if agent_run is not None:
        AgentRun.objects.filter(pk=agent_run.pk).update(
            current_step=len(steps),
            result={"used_tool": used_tool, "intent": intent, "citations": len(citations)},
        )

    parts: list[str] = []
    saved = False

    def _persist():
        nonlocal saved
        if saved:
            return None
        saved = True
        answer = "".join(parts).strip()
        meta = {"citations": citations, "used_tool": used_tool, "steps": steps, "intent": intent}
        if proposal is not None:
            # The proposal rides in the assistant message meta (status starts "pending"); the card is
            # keyed by this message id and the execute endpoint re-reads the payload from here.
            meta["proposal"] = {**proposal, "status": "pending"}
        if import_task is not None:
            # The import card rides in meta too (mapping stage); preview/execute re-read the file +
            # target from here, keyed by this message id, and execute persists the report back.
            meta["import"] = import_task
        if suggestion is not None:
            # Same ride for a suggestion card; ``pending`` is the blocked decision session 13
            # replays once the user returns from the detour.
            meta["suggestion"] = {**suggestion, "status": "open"}
            if pending is not None:
                meta["pending"] = pending
        if checkpoint_message is not None:
            # Same row the periodic partial-content checkpoint (worker task) was writing into —
            # this is the authoritative final write, always the last thing to touch it.
            checkpoint_message.content = answer
            checkpoint_message.meta = meta
            checkpoint_message.save(update_fields=["content", "meta"])
            msg = checkpoint_message
        else:
            msg = conversation.messages.create(role="assistant", content=answer, meta=meta)
        conversation.save()  # touch updated_at after the reply lands
        audit.record(
            module="assistant", action="ask", entity_type="Question", entity_id=used_tool or "none",
            actor=actor, after={"tools": [s["tool"] for s in steps], "citations": len(citations)},
        )
        return msg

    sys_meta: dict = {}
    data_meta: dict = {}
    try:
        if clarify_text is not None:
            # A clarifying question IS the answer for this turn — no model stream, no citations.
            parts.append(clarify_text)
            citations = []
            yield {"type": "token", "text": clarify_text}
        else:
            data_section = envelope.Section(
                "answer_data", 0,
                json.dumps([{"tool": r["tool"], "result": r["data"]} for r in results],
                          ensure_ascii=False),
                degrade_fn=_degrade_list_half,
            )
            kept_data, data_meta = envelope.assemble([data_section], model=model, max_tokens=max_tokens)
            user = json.dumps(
                {"question": q, "data": json.loads(kept_data.get("answer_data", "[]"))},
                ensure_ascii=False,
            )
            if file_notes:
                user += "\n\nAttached files:\n" + "\n\n".join(file_notes)
            if proposal is not None:
                # A draft is ready but NOT created yet — narrate it, invite confirm/dismiss below.
                user += ("\n\nA draft has been prepared for the user to review. Briefly say what it "
                         "will create and mention they can confirm or dismiss it below; do NOT claim "
                         "it was created or posted.")
            if import_task is not None:
                # A mapping-stage import card is shown below — narrate it, never claim any create.
                user += ("\n\nA spreadsheet import has been prepared: its columns are mapped to fields "
                         "and shown in a card below. Briefly say you read the file (name the target and "
                         "row count if useful), and that they can adjust the column mapping and preview "
                         "the rows before anything is created. Do NOT claim any records were created.")
            if suggestion is not None:
                # Issue → fix → the promised return: the card carries the buttons; the prose
                # carries the plan ("After you save the supplier, I'll bring you back...").
                user += ("\n\nA fix-it card is shown below your reply. Briefly explain, in order: "
                         "what is blocking the request, the fastest fix the card offers, and that "
                         "after they fix it you will continue"
                         + (f" ({suggestion['resume']})" if suggestion.get("resume") else "")
                         + ". Do NOT claim anything was created or fixed yet.")
            answer_system, sys_meta = _answer_system(actor, page, conversation, q, model=model)
            _t0 = time.monotonic()
            _first = True
            _retrying = {"n": 0}
            for chunk in complete_stream(
                [{"role": "user", "content": user}], system=answer_system, media=media,
                on_retry=lambda: _retrying.__setitem__("n", _retrying["n"] + 1),
            ):
                if _retrying["n"]:
                    # T2.6: the provider dropped mid-answer and the gateway is restarting the turn
                    # on the next chain model — a calm inline notice, never a raw error.
                    yield {"type": "retrying"}
                    _retrying["n"] = 0
                if _first:
                    trace.mark_ttft()
                    _first = False
                parts.append(chunk)
                yield {"type": "token", "text": chunk}
            trace.step(kind="llm", name="answer", ok=True,
                      latency_ms=int((time.monotonic() - _t0) * 1000),
                      detail={"prompt_ref": _answer_prompt_ref()})
            total_in_tokens += estimate_tokens(answer_system + user)
            total_out_tokens += estimate_tokens("".join(parts))
        trace.usage(provider=provider(), model=model, estimated=True,
                   input_tokens=total_in_tokens, output_tokens=total_out_tokens)
        # T3.6: the final composition this run actually assembled — system-prompt sections, the
        # last round's planner history/gathered, and the answer's own data payload.
        trace.meta["envelope"] = {"system": sys_meta, "planner_data": loop_envelope_meta,
                                  "answer_data": data_meta}
        yield {"type": "citations", "citations": citations}
        msg = _persist()
        if msg is not None and conversation is not None:
            # T3.7: post-response only — never blocks this stream (fire-and-forget Celery task).
            summarize.maybe_trigger(conversation)
        if proposal is not None and msg is not None:
            yield {"type": "proposal", "message_id": msg.id,
                   "proposal": {**proposal, "status": "pending"}}
        if import_task is not None and msg is not None:
            yield {"type": "import", "message_id": msg.id, "import": import_task}
        if suggestion is not None and msg is not None:
            yield {"type": "suggestion", "message_id": msg.id,
                   "suggestion": {**suggestion, "status": "open"}}
        # T3.6 step 5: lets the client render a quiet usage meter and, when this turn actually
        # trimmed or dropped something, a calm compaction notice instead of silent truncation.
        yield {"type": "done", "message_id": msg.id, "used_tool": used_tool,
               "conversation_tokens": total_in_tokens + total_out_tokens,
               "budget_tokens": envelope.budget_for(model, max_tokens),
               "compacted": _any_compacted(sys_meta, loop_envelope_meta, data_meta)}
    finally:
        _persist()  # disconnect / error mid-stream still saves the partial answer


def resume_detour(*, actor, conversation, source_message, resolved):
    """Continue a paused suggestion after a guided detour (plan session 13) — the return half of the
    session-12 promise. ``source_message`` is the assistant turn carrying the suggestion card and its
    ``meta.pending`` (the blocked ``propose`` decision). ``resolved`` is the record the user just
    created (``{entity, id, label}``) or ``None`` (they returned via "I'm done" without our capturing
    one — the rebuild re-resolves the reference by its original query).

    Settles the card (single-use, reload-safe), records an honest ``detour_return`` user turn, rebuilds
    the paused proposal against the now-existing record, and streams a welcome-back that either carries
    the re-prepared draft or says calmly it's still missing (re-opening the card). Yields the same SSE
    events as :func:`run`. It NEVER re-runs the planner or the vision path: the extraction that
    produced the paused args is reused, never redone (Task D). Tests monkeypatch ``complete_stream``.
    """
    meta = source_message.meta or {}
    pending = meta.get("pending") or {}
    suggestion_meta = meta.get("suggestion") or {}
    issue = suggestion_meta.get("issue") or {}
    entity = issue.get("entity") or (resolved or {}).get("entity") or "record"
    label = (resolved or {}).get("label") or issue.get("query") or ""

    # Settle the card first so a reload shows it resolved (mirrors a consumed proposal). If the
    # rebuild finds the record still missing we re-open it below.
    suggestion_meta["status"] = "resolved"
    source_message.meta = meta
    source_message.save(update_fields=["meta"])

    # An honest synthetic turn: recorded in the transcript, flagged so the UI renders a calm
    # "returned" divider (localised) rather than an English user bubble. entity/label ride in meta
    # for that localisation.
    if resolved:
        note = (f"Detour complete: {entity} {label} ({resolved.get('id', '')}) now exists. "
                "Resume the pending work.")
    else:
        note = (f"Detour complete — back from creating the {entity}. "
                f"Re-check whether '{issue.get('query', '')}' exists now and resume.")
    conversation.messages.create(
        role="user", content=note,
        meta={"kind": "detour_return", "entity": entity, "label": label},
    )
    conversation.save()

    # Rebuild the paused proposal — the missing record now exists, so ``build`` re-resolves it. No
    # planner, no tools: just the one blocked resolution retried against fresh data.
    pname = pending.get("name") or ""
    built = actions.build(actor, pname, dict(pending)) if pname else {"error": "nothing to resume"}
    proposal: dict | None = None
    still_blocked = "blocker" in built
    if still_blocked:
        # The record the user was sent to create still can't be found — re-open the original card.
        suggestion_meta["status"] = "open"
        source_message.meta = meta
        source_message.save(update_fields=["meta"])
    elif "error" not in built:
        proposal = {**built, "status": "pending"}

    if proposal is not None:
        instruction = (
            f"The user just returned from creating {entity} '{label}'. Welcome them back warmly and "
            "briefly by name of that record, then say the draft you had paused is ready again below "
            "and they can confirm or dismiss it. Do NOT claim anything was created or posted.")
    elif still_blocked:
        instruction = (
            f"The user returned but the {entity} '{issue.get('query', '')}' still can't be found. "
            "Tell them calmly and blame-free that it's still missing, and that the fix-it options are "
            "open again above. Do NOT claim anything was created.")
    else:
        instruction = (
            "The user returned from a detour but the paused work could not be re-prepared. Explain "
            "calmly what you can and invite them to say again what to create. Do NOT claim success.")

    citations: list[dict] = []
    steps: list[dict] = []
    used_tool = None
    intent = "create"
    parts: list[str] = []
    saved = False

    def _persist():
        nonlocal saved
        if saved:
            return None
        saved = True
        answer = "".join(parts).strip()
        out = {"citations": citations, "used_tool": used_tool, "steps": steps,
               "intent": intent, "kind": "detour_return_reply"}
        if proposal is not None:
            out["proposal"] = {**proposal}
        msg = conversation.messages.create(role="assistant", content=answer, meta=out)
        conversation.save()
        audit.record(
            module="assistant", action="detour_resume", entity_type="Question",
            entity_id=pname or "none", actor=actor,
            after={"entity": entity, "resolved": bool(resolved), "proposal": proposal is not None},
        )
        return msg

    model = model_id()
    max_tokens = settings.ASSISTANT_MAX_TOKENS
    try:
        user = json.dumps(
            {"detour_return": note, "record": resolved, "proposal_ready": proposal is not None},
            ensure_ascii=False,
        )
        # A detour has no new question of its own — the reply language follows the last thing the
        # user actually wrote in this conversation.
        answer_system, sys_meta = _answer_system(
            actor, None, conversation, _last_user_text(conversation), model=model)
        _retrying = {"n": 0}
        for chunk in complete_stream(
            [{"role": "user", "content": user + "\n\n" + instruction}],
            system=answer_system,
            on_retry=lambda: _retrying.__setitem__("n", _retrying["n"] + 1),
        ):
            if _retrying["n"]:
                yield {"type": "retrying"}
                _retrying["n"] = 0
            parts.append(chunk)
            yield {"type": "token", "text": chunk}
        yield {"type": "citations", "citations": citations}
        msg = _persist()
        if msg is not None:
            summarize.maybe_trigger(conversation)  # T3.7: post-response only, never blocks the stream
        if proposal is not None and msg is not None:
            yield {"type": "proposal", "message_id": msg.id, "proposal": {**proposal}}
        yield {"type": "done", "message_id": msg.id if msg else None, "used_tool": used_tool,
               "conversation_tokens": estimate_tokens(answer_system + user + "".join(parts)),
               "budget_tokens": envelope.budget_for(model, max_tokens),
               "compacted": _any_compacted(sys_meta)}
    finally:
        _persist()  # disconnect / error mid-stream still saves the partial welcome-back
