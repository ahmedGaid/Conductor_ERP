"""Builds the system prompt: who the user is, where they are, what Conductor is.

The model never asks for information this envelope already carries. Rebuilt fresh on every
request (never cached stale) so a permission or page change is reflected immediately.
"""
from __future__ import annotations

from erp.identity import access, services as identity_services

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
        "Never reveal or act beyond these permissions. If a question reaches into a module not "
        "listed above, say plainly and calmly that it is outside the user's access.",
    ]
    return "\n".join(lines)


def _page_block(page: dict | None) -> str | None:
    if not page:
        return None
    lines = ["Page:"]
    module = page.get("module")
    if module:
        lines.append(f"- The user is currently in the {module} module, at route {page.get('path', '')}.")
    record = page.get("record")
    if record and record.get("label"):
        lines.append(f"- They are viewing {record.get('type', 'record')} {record['label']}.")
    recent = page.get("recent") or []
    if recent:
        lines.append(f"- Recently visited: {', '.join(recent)}.")
    return "\n".join(lines) if len(lines) > 1 else None


def _company_block() -> str:
    org = identity_services.get_org_preferences()
    name = org.company_name or "the company"
    return (
        f"Company: {name}, based in {org.country or 'Egypt'}. Base currency is "
        f"{org.base_currency} (integer minor units on the wire; format only when phrasing the "
        "answer). VAT-registered accounting applies."
    )


def build_system_prompt(actor, page: dict | None = None) -> str:
    """Assemble the envelope: identity, user, page (optional), company, personas."""
    sections = [_IDENTITY, _user_block(actor)]
    page_section = _page_block(page)
    if page_section:
        sections.append(page_section)
    sections.append(_company_block())
    sections.append(_PERSONA)
    return "\n\n".join(sections)
