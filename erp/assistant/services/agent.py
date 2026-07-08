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
from ..query_registry import REGISTRY as _QUERY_REGISTRY
from ..query_registry import query_grammar_text
from ..tools import TOOLS, catalog_text
from . import actions, context, files, imports, suggestions
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
    "Choosing a source: live business data (balances, stock, orders, invoices, totals) MUST come "
    "from the data tools; anything defined by company documents (policies, SOPs, procedures, "
    "catalog details, contract terms) MUST come from search_documents; when a question needs "
    "both, gather both before answering. Conversation history is context, never a source of "
    "business facts. Never choose answer for a documentation question, and never name, quote, or "
    "attribute to a document, before calling search_documents THIS turn — a document you have "
    "not retrieved with search_documents is invented and forbidden, even if one was searched "
    "earlier in the conversation. If search_documents finds nothing, say no document covers it — "
    "never invent documentation.\n"
    "The query_data tool is the flexible fallback for ANY lookup, list, count, or total no "
    "specific tool covers (e.g. 'list the items', 'show the quotations'). Its data "
    "sets and their allowed fields are:\n{query_grammar}\n"
    "For query_data set entity to a data set above and only use fields listed for it; put "
    "comparisons in filters as {{field, op, value}}, break-downs in group_by, and set aggregate "
    "('list' returns the rows themselves; sum/avg/min/max need metric).\n"
    "When the user asks you to CREATE/MAKE/ADD/RAISE a record, do not use a data tool — propose a "
    "write action instead. Never answer with UI navigation instructions ('go to the sales module "
    "and use…') for something you can propose: if the request names what an action needs, propose "
    "it; if the specifics are missing (which customer, which items), clarify to get them — the one "
    "thing you never do is describe the manual way. You have these proposable actions (each only "
    "prepares a DRAFT the user confirms; you never create anything yourself):\n{action_catalog}\n"
    "Attachments: when the user attaches an image or PDF (an invoice, a purchase order, a photo of "
    "one) it is given to you directly — READ it. When they say 'create a PO from the attached image' "
    "or similar, extract the supplier and the line items (item, quantity, and unit cost when shown) "
    "straight from it and fill the propose action's fields. Never ask the user to retype what the "
    "attachment plainly shows, and never invent lines you cannot actually see — if the image is "
    "unreadable or a value is genuinely absent, say so or leave that field null.\n"
    "Importing a list: when the user attaches a CSV or Excel spreadsheet and asks to import/load/add "
    "it as customers, suppliers, or items (a whole list at once, not one record), choose action "
    "import and set target to customers/suppliers/items when it's clear (leave null to auto-detect). "
    "The system reads the file, maps its columns, and shows a preview the user confirms before any "
    "record is created — do not propose single records for a bulk list, and never claim rows were "
    "created.\n"
    "Each round respond with EXACTLY ONE JSON object, one of:\n"
    '  {{"action": "tool", "tool": "<name>", "why": "<=8 words, shown to the user>", <args...>}}\n'
    '  {{"action": "propose", "name": "<action>", "why": "<=8 words>", <action args...>}}\n'
    '  {{"action": "import", "target": "<customers|suppliers|items|null>", "why": "<=8 words>"}}\n'
    '  {{"action": "clarify", "question": "<one short question>"}}\n'
    '  {{"action": "suggest", "resume": "<one sentence: what you will continue once it is fixed>"}}\n'
    '  {{"action": "answer"}}\n'
    "On your first decision of a turn, also set intent (lookup/report/document_search/create/"
    "update/workflow/file/explain/conversation/mixed) — it routes nothing by itself but is "
    "recorded; classify honestly.\n"
    "Fill only the arguments the chosen tool/action needs; leave the rest null. Gather with as few "
    "tool calls as the question needs — you may call several tools across rounds to combine data from "
    "different areas. When you have enough to answer fully, choose answer. Choose propose as soon as "
    "you have what an action needs (gather first if you must, e.g. low-stock before a purchase "
    "request). Choose clarify ONLY when the request is too vague to act on — never to stall. Never "
    "offer or ask permission to look something up ('shall I check…?') — if a tool can answer it, run "
    "the tool. Never use clarify for a yes/no 'should I go ahead?' — proposing shows a confirm card "
    "and THAT is the confirmation; clarify only asks for missing specifics (which supplier, which "
    "items, what quantities). A result "
    "shaped {{\"error\": ...}} means that path is blocked or wrong: read it and try different "
    "arguments/tool, or answer honestly — never repeat the same failing call. A result shaped "
    "{{\"blocker\": ...}} means a record the request depends on is missing, inactive, or ambiguous: "
    "choose suggest — the system shows the user a fix-it card with their permitted options; set "
    "resume to the one thing you will continue after the fix (e.g. 'I will prepare the sales order "
    "for ABC Trading'). Never retry the same missing reference and never invent the record. 'why' "
    "is a short human phrase like 'Checking this month's sales'. Never invent data; only these "
    "tools can see it."
)

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


def _answer_system(actor, page: dict | None, conversation=None) -> str:
    # Same envelope + data-answering constraints as the single-shot path; DATA now holds every
    # round's result rather than one.
    return context.build_system_prompt(actor, page, conversation) + "\n\n" + _ANSWER_TONE


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

    history = _recent_turns(conversation, exclude_id=user_msg.id if user_msg else None)

    # --- the loop: plan → run a tool → repeat, until answer / clarify / round cap -----------------
    loop_system = _LOOP_SYSTEM.format(catalog=catalog_text(), query_grammar=query_grammar_text(),
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

    for _round in range(MAX_ROUNDS):
        # media rides every round: the planner keeps its eyes on the attachment until it proposes
        # (usually round 1), so it can read supplier/lines from an image instead of guessing them.
        decision = complete_json(loop_system, _loop_user(q, history, results, file_notes),
                                 _LOOP_SCHEMA, media=media)
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
            results.append({"tool": name, "why": why, "data": {
                "error": "You already ran this exact call this turn. Use its earlier result, "
                         "change the arguments, or answer."}})
            continue
        seen_calls.add(signature)
        yield {"type": "step", "tool": name, "label": why, "state": "running"}
        data, ok = _run_tool(actor, decision)
        blocked = isinstance(data, dict) and "blocker" in data
        if blocked:  # no tool emits blockers today, but the convention is tool-wide (Task A)
            last_blocker = data["blocker"]
        results.append({"tool": name, "why": why, "data": data})
        steps.append({"tool": name, "why": why, "ok": ok and not blocked})
        if ok and not blocked:
            tool = TOOLS.get(name)
            citations.extend(tool.cite(data) if tool else [])
        yield {"type": "step", "tool": name, "label": why, "state": "done", "ok": ok and not blocked}

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
        yield {"type": "step", "tool": name, "label": why, "state": "running"}
        data, ok = _run_tool(actor, {"tool": name, "query": q})
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
        yield {"type": "step", "tool": name, "label": why, "state": "running"}
        data, ok = _run_tool(actor, {**last_decision, "tool": name})
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
        msg = conversation.messages.create(role="assistant", content=answer, meta=meta)
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
            for chunk in complete_stream(
                [{"role": "user", "content": user}],
                system=_answer_system(actor, page, conversation), media=media,
            ):
                parts.append(chunk)
                yield {"type": "token", "text": chunk}
        yield {"type": "citations", "citations": citations}
        msg = _persist()
        if proposal is not None and msg is not None:
            yield {"type": "proposal", "message_id": msg.id,
                   "proposal": {**proposal, "status": "pending"}}
        if import_task is not None and msg is not None:
            yield {"type": "import", "message_id": msg.id, "import": import_task}
        if suggestion is not None and msg is not None:
            yield {"type": "suggestion", "message_id": msg.id,
                   "suggestion": {**suggestion, "status": "open"}}
        yield {"type": "done", "message_id": msg.id, "used_tool": used_tool}
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

    try:
        user = json.dumps(
            {"detour_return": note, "record": resolved, "proposal_ready": proposal is not None},
            ensure_ascii=False,
        )
        for chunk in complete_stream(
            [{"role": "user", "content": user + "\n\n" + instruction}],
            system=_answer_system(actor, None, conversation),
        ):
            parts.append(chunk)
            yield {"type": "token", "text": chunk}
        yield {"type": "citations", "citations": citations}
        msg = _persist()
        if proposal is not None and msg is not None:
            yield {"type": "proposal", "message_id": msg.id, "proposal": {**proposal}}
        yield {"type": "done", "message_id": msg.id if msg else None, "used_tool": used_tool}
    finally:
        _persist()  # disconnect / error mid-stream still saves the partial welcome-back
