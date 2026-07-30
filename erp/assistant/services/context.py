"""Builds the system prompt: who the user is, where they are, what Conductor is.

The model never asks for information this envelope already carries. Rebuilt fresh on every
request (never cached stale) so a permission or page change is reflected immediately.
"""
from __future__ import annotations

from erp.accounting import contracts as accounting
from erp.identity import access
from erp.identity import services as identity_services
from erp.inventory import contracts as inventory

from ..gateway.core import model_id
from . import envelope
from . import memory as memory_service
from . import page_distill
from .prompt_registry import get as get_prompt

_identity_prompt = get_prompt("identity")
_persona_prompt = get_prompt("persona")
_sources_prompt = get_prompt("sources")

_IDENTITY = _identity_prompt.template
_PERSONA = _persona_prompt.template
_SOURCES = _sources_prompt.template

# The static envelope's combined prompt ref — callers building the full answer system prompt
# (ask.py/agent.py, which append their own closing block) join this with their own prompt's ref.
CONTEXT_PROMPT_REF = "+".join((_identity_prompt.ref, _persona_prompt.ref, _sources_prompt.ref))

# module -> Arabic module label (Identity System §6.1); kept local to the prompt, not user-facing UI.
_MODULE_LABELS = {
    "accounting": "المالية",
    "inventory": "المخزون",
    "sales": "المبيعات",
    "purchasing": "المشتريات",
    "crm": "علاقات العملاء",
    "einvoice": "الفوترة الإلكترونية",
    "notifications": "الإشعارات",
    "workflow": "سير العمل",
    "administration": "الإدارة",
}


def _user_block(actor) -> str:
    modules = access.accessible_modules(actor)
    module_list = ", ".join(modules) if modules else "none"
    display_name = identity_services.get_preferences(actor).display_name
    lines = [
        f"User: {actor.get_username()} ({display_name or actor.get_username()}).",
        f"Roles: {', '.join(actor.roles) or 'none'}.",
        f"Accessible modules: {module_list}.",
        "Never reveal or act beyond these permissions. Only say a question is outside the user's "
        "access when it is about a module NOT in the list above. If the module IS in the list but "
        "DATA is empty because no report exists for that exact question yet, that is NOT a "
        "permission issue — say plainly that Conductor does not have that specific report yet, "
        "never blame access.",
    ]
    return "\n".join(lines)


def _page_block(actor, page: dict | None) -> str | None:
    if not page:
        return None
    lines = ["Page:"]
    language = page.get("language")
    if language:
        label = "Arabic" if language == "ar" else "English"
        lines.append(f"- The interface is set to {label}, but this does NOT decide your reply "
                     f"language — match the language of the user's latest message; use {label} only "
                     "when their message language is genuinely unclear.")
    module = page.get("module")
    if module:
        lines.append(f"- The user is currently in the {module} module, at route {page.get('path', '')}.")
    record = page.get("record")
    if record and record.get("label"):
        if page.get("detached"):
            # The user detached the record from this conversation — it stays visible as background
            # so navigation still makes sense, but it is never the implied subject of a question.
            lines.append(
                f"- The page shows {record.get('type', 'record')} {record['label']} in the "
                "background, but the user detached it from this conversation — do NOT treat it "
                "as the subject of their questions; if a reference is ambiguous, ask which "
                "record they mean."
            )
        else:
            lines.append(f"- They are viewing {record.get('type', 'record')} {record['label']}.")
            # T3.8: a compact typed snapshot (status/amounts/counts) in place of the model reaching
            # for a full detail tool just to answer "what's the status/margin on this" — table-driven
            # per record type (page_distill.py), fails open to no line at all when unregistered/gone.
            snapshot = page_distill.render(actor, record.get("type"), record.get("id"))
            if snapshot:
                lines.append(f"- Record detail: {snapshot}.")
    recent = page.get("recent") or []
    if recent:
        lines.append(f"- Recently visited: {', '.join(recent)}.")
    filters = page.get("filters") or {}
    if filters:
        rendered = ", ".join(f"{k}={v}" for k, v in list(filters.items())[:10])
        lines.append(f"- Active list filters: {rendered}.")
    if page.get("dirty"):
        lines.append("- The user has UNSAVED form changes on this page: never suggest "
                     "navigation that would lose them without saying so.")
    return "\n".join(lines) if len(lines) > 1 else None


def _company_block(actor) -> str:
    org = identity_services.get_org_preferences()
    name = org.company_name or "the company"
    lines = [
        f"Company: {name}, based in {org.country or 'Egypt'}. Base currency is "
        f"{org.base_currency} (integer minor units on the wire; format only when phrasing the "
        "answer). VAT-registered accounting applies."
    ]
    branch = getattr(actor, "branch", None)
    if branch is not None:
        lines.append(f"The user's branch is {branch.name}.")
    warehouse_code = inventory.default_warehouse_code()
    if warehouse_code:
        lines.append(f"Default warehouse: {warehouse_code}.")
    fiscal = accounting.current_fiscal_period()
    if fiscal and fiscal.get("period_code"):
        lines.append(
            f"Current accounting period: {fiscal['period_code']} "
            f"(fiscal year {fiscal.get('fiscal_year_code') or 'unset'}, "
            f"{fiscal.get('period_status') or 'unknown'})."
        )
    return " ".join(lines)


def _degrade_page_block(text: str) -> str | None:
    """Drop the lines most likely to run long (active filters, recently-visited list, the T3.8
    record-detail snapshot) before dropping the whole page section — the bare record/module lines
    are what the model actually needs."""
    lines = text.split("\n")
    kept = [ln for ln in lines
            if not (ln.startswith("- Active list filters:") or ln.startswith("- Recently visited:")
                    or ln.startswith("- Record detail:"))]
    return "\n".join(kept) if len(kept) < len(lines) and len(kept) > 1 else None


def _degrade_recent_actions_block(text: str) -> str | None:
    """Keep only the most recent proposal line instead of up to 5 — "suggestions context" is the
    lowest-priority section (T3.6), so it gives way first under budget pressure."""
    lines = text.split("\n")
    header, bullets = lines[0], lines[1:]
    if len(bullets) <= 1:
        return None
    return "\n".join([header, *bullets[-1:]])


def _recent_actions_block(conversation) -> str | None:
    if conversation is None:
        return None
    proposals = []
    for message in conversation.messages.filter(role="assistant").order_by("-created_at")[:20]:
        proposal = (message.meta or {}).get("proposal")
        if proposal:
            proposals.append(proposal)
        if len(proposals) == 5:
            break
    if not proposals:
        return None
    lines = ["Previous AI actions:"]
    for proposal in reversed(proposals):
        lines.append(f"- Recently proposed/executed: {proposal.get('action')} "
                     f"({proposal.get('status')}).")
    return "\n".join(lines)


def detect_language(text: str) -> str:
    """``"ar"`` if the text carries Arabic script, else ``"en"``.

    Deliberately a character test, not a model call: the reply language must be decided the same
    way every time, and a one-word question ("Sales?") has to resolve without inference.
    """
    return "ar" if any("؀" <= ch <= "ۿ" for ch in (text or "")) else "en"


def answer_language_directive(question: str) -> str:
    """The closing, non-negotiable reply-language line for one question.

    Asking the model to *infer* "match the user's language" loses against an Arabic-heavy system
    prompt — live recordings had gemini-2.5-flash answering English questions in Arabic 21/21
    even with the rule stated last. So the language is computed here and stated flatly, leaving
    the model nothing to weigh up.
    """
    if detect_language(question) == "ar":
        return "REPLY LANGUAGE: Arabic. The user wrote in Arabic — your entire answer must be in Arabic."
    return (
        "REPLY LANGUAGE: English. The user wrote in English — your entire answer must be in "
        "English. Do NOT answer in Arabic. Arabic terms elsewhere in these instructions are "
        "vocabulary references only."
    )


def build_system_prompt_with_meta(actor, page: dict | None = None, conversation=None,
                                  *, model: str | None = None,
                                  message: str = "") -> tuple[str, dict]:
    """Assemble the envelope: identity, user, page (optional), company, recent actions, personas —
    fitted to ``model``'s token budget (T3.6) instead of joined unconditionally. Returns
    ``(prompt, meta)``; ``meta`` is the per-section composition record for ``Trace.meta.envelope``.

    Priority order below IS render order (envelope.assemble never reorders) — identity+persona and
    the answering rules stay first/last exactly as before; only the two genuinely unbounded blocks
    (page enrichment, recent-actions) have a shorter form to fall back to under real pressure. At
    this envelope's actual size (a few hundred to low thousands of tokens) against any of the four
    providers' windows, trimming essentially never fires today — the guarantee is structural, for
    when a page/conversation payload grows.
    """
    from django.conf import settings

    sections = [envelope.Section("identity", 0, _IDENTITY)]
    sections.append(envelope.Section("user", 1, _user_block(actor)))
    page_section = _page_block(actor, page)
    if page_section:
        sections.append(envelope.Section("page", 2, page_section, max_share=0.3,
                                         degrade_fn=_degrade_page_block))
    # Memory (T4.5): below the page snapshot (what the user is looking at right now still wins),
    # above the company/retrieval blocks. Capped at a tenth of the budget and degraded facts-first —
    # a slot decides behaviour, a fact only colours the answer.
    memory_block = memory_service.recall(actor, message)
    if memory_block:
        sections.append(envelope.Section("memory", 3, memory_block, max_share=0.1,
                                         degrade_fn=memory_service.degrade_block))
    sections.append(envelope.Section("company", 4, _company_block(actor)))
    recent_actions = _recent_actions_block(conversation)
    if recent_actions:
        sections.append(envelope.Section("suggestions", 5, recent_actions, max_share=0.2,
                                         degrade_fn=_degrade_recent_actions_block))
    sections.append(envelope.Section("persona", 6, _PERSONA))
    sections.append(envelope.Section("sources", 7, _SOURCES))

    kept, meta = envelope.assemble(
        sections, model=model or model_id(), max_tokens=settings.ASSISTANT_MAX_TOKENS)
    return "\n\n".join(kept.values()), meta


def build_system_prompt(actor, page: dict | None = None, conversation=None,
                        *, message: str = "") -> str:
    """Same as ``build_system_prompt_with_meta`` without the composition record — the call sites
    that don't (yet) hold a trace handle to record it against."""
    return build_system_prompt_with_meta(actor, page, conversation, message=message)[0]
