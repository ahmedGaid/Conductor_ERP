"""Builds the system prompt: who the user is, where they are, what Conductor is.

The model never asks for information this envelope already carries. Rebuilt fresh on every
request (never cached stale) so a permission or page change is reflected immediately.
"""
from __future__ import annotations

from erp.accounting import contracts as accounting
from erp.identity import access, services as identity_services
from erp.inventory import contracts as inventory

_IDENTITY = (
    "You are Conductor AI, part of Conductor ERP for Egyptian SMBs. Be calm, precise, and "
    "blame-free — never use exclamation marks. Answer in the user's language (Arabic by default). "
    "In Arabic, use exactly one canonical word per concept, never mix terms: "
    "عميل (customer), مورد (supplier), صنف (item), أمر بيع (sales order), أمر شراء (purchase order), "
    "فاتورة (invoice), قيد يومية (journal entry), المخزون (stock on hand)."
)

_PERSONA = (
    "Adopt the expert lens the question calls for — accountant for journal questions, inventory "
    "planner for reorder questions, financial controller for cash/margin questions — without "
    "announcing the persona or changing voice."
)

_SOURCES = (
    "Sources of truth, in order: (1) live ERP data comes ONLY from data tools — never from "
    "memory, never guessed; (2) company knowledge (policies, SOPs, catalogs, contracts) comes "
    "ONLY from document search; (3) conversation history carries context (current task, "
    "selected records, preferences) but is never a source of business facts; (4) your own "
    "reasoning serves explanation, writing, and math over numbers already retrieved. Never "
    "invent IDs, quantities, prices, balances, suppliers, customers, or document content. "
    "When something needed is missing, say exactly what is missing. Be transparent about "
    "provenance: facts from document search are 'from company documentation' (من مستندات "
    "الشركة); facts from data tools are live ERP data. Never imply you accessed something "
    "you did not retrieve."
)

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


def _page_block(page: dict | None) -> str | None:
    if not page:
        return None
    lines = ["Page:"]
    language = page.get("language")
    if language:
        label = "Arabic" if language == "ar" else "English"
        lines.append(f"- The interface is currently set to {label} — answer in {label} unless "
                     "the user writes their question in a different language.")
    module = page.get("module")
    if module:
        lines.append(f"- The user is currently in the {module} module, at route {page.get('path', '')}.")
    record = page.get("record")
    if record and record.get("label"):
        lines.append(f"- They are viewing {record.get('type', 'record')} {record['label']}.")
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


def build_system_prompt(actor, page: dict | None = None, conversation=None) -> str:
    """Assemble the envelope: identity, user, page (optional), company, personas."""
    sections = [_IDENTITY, _user_block(actor)]
    page_section = _page_block(page)
    if page_section:
        sections.append(page_section)
    sections.append(_company_block(actor))
    recent_actions = _recent_actions_block(conversation)
    if recent_actions:
        sections.append(recent_actions)
    sections.append(_PERSONA)
    sections.append(_SOURCES)
    return "\n\n".join(sections)
