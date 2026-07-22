"""Five fixed workflow templates — the non-technical builder's front door.

Each template is a pure function: params in, a (nodes, edges, trigger) graph out, in exactly
the shape `services.save_graph()` and `triggers.create_trigger()` already accept. No new engine
concepts — a template is just a pre-built linear/one-branch WorkflowNode/WorkflowEdge graph.
"""
from __future__ import annotations

from erp.core.errors import ValidationError
from erp.purchasing.events import PR_SUBMITTED

TEMPLATE_CATALOG: list[dict] = [
    {
        "id": "approval_above_amount",
        "name": {"ar": "طلب موافقة عند تجاوز مبلغ", "en": "Ask for approval above an amount"},
        "fields": [
            {"key": "amount_minor", "type": "money",
             "label": {"ar": "المبلغ", "en": "Amount"}},
            {"key": "approver_role", "type": "role",
             "label": {"ar": "من يوافق", "en": "Who approves"}},
        ],
    },
    {
        "id": "low_stock_alert",
        "name": {"ar": "تنبيه عند انخفاض المخزون", "en": "Alert when stock is low"},
        "fields": [
            {"key": "recipient", "type": "person",
             "label": {"ar": "من يُخطَر", "en": "Who to notify"}},
        ],
    },
    {
        "id": "overdue_invoice_reminder",
        "name": {"ar": "تذكير بالفواتير المتأخرة", "en": "Remind about overdue invoices"},
        "fields": [
            {"key": "days_overdue", "type": "number",
             "label": {"ar": "عدد أيام التأخير", "en": "Days overdue"}},
            {"key": "recipient", "type": "person",
             "label": {"ar": "من يُخطَر", "en": "Who to notify"}},
        ],
    },
    {
        "id": "new_lead_followup",
        "name": {"ar": "متابعة العملاء المحتملين الجدد", "en": "Follow up on new leads"},
        "fields": [
            {"key": "days_since_created", "type": "number",
             "label": {"ar": "بعد كم يوم", "en": "After how many days"}},
        ],
    },
    {
        "id": "ticket_escalation",
        "name": {"ar": "تصعيد تذاكر الدعم المتأخرة", "en": "Escalate overdue support tickets"},
        "fields": [],
    },
]

_CATALOG_BY_ID = {t["id"]: t for t in TEMPLATE_CATALOG}


def _approval_above_amount(params: dict) -> dict:
    amount = params["amount_minor"]
    role = params["approver_role"]
    nodes = [
        {"key": "start", "type": "start", "config": {}, "position": {"x": 0, "y": 0}},
        {"key": "check_amount", "type": "condition", "config": {}, "position": {"x": 200, "y": 0}},
        {"key": "ask_approval", "type": "approval",
         "config": {"title": "Approval needed", "approver_role": role},
         "position": {"x": 400, "y": 0}},
        {"key": "end", "type": "end", "config": {}, "position": {"x": 600, "y": 0}},
    ]
    edges = [
        {"source": "start", "target": "check_amount", "ordering": 0, "condition": None},
        {"source": "check_amount", "target": "ask_approval", "ordering": 0,
         "condition": {">": [{"var": "amount_minor"}, amount]}},
        {"source": "check_amount", "target": "end", "ordering": 1, "condition": None},
        {"source": "ask_approval", "target": "end", "ordering": 0, "condition": None},
    ]
    trigger = {"event_name": PR_SUBMITTED, "condition": {">": [{"var": "amount_minor"}, amount]}}
    return {"nodes": nodes, "edges": edges, "trigger": trigger, "schedule": None}


def _low_stock_alert(params: dict) -> dict:
    recipient = params["recipient"]
    nodes = [
        {"key": "start", "type": "start", "config": {}, "position": {"x": 0, "y": 0}},
        {"key": "notify", "type": "notification",
         "config": {"channel": "inapp", "recipient": recipient,
                    "subject": "Low stock: {{ ctx.item_name }}",
                    "body": "{{ ctx.item_name }} is below its reorder point."},
         "position": {"x": 200, "y": 0}},
        {"key": "end", "type": "end", "config": {}, "position": {"x": 400, "y": 0}},
    ]
    edges = [
        {"source": "start", "target": "notify", "ordering": 0, "condition": None},
        {"source": "notify", "target": "end", "ordering": 0, "condition": None},
    ]
    return {"nodes": nodes, "edges": edges, "trigger": None, "schedule": "low_stock"}


def _overdue_invoice_reminder(params: dict) -> dict:
    recipient = params["recipient"]
    nodes = [
        {"key": "start", "type": "start", "config": {}, "position": {"x": 0, "y": 0}},
        {"key": "notify", "type": "notification",
         "config": {"channel": "inapp", "recipient": recipient,
                    "subject": "Overdue invoice: {{ ctx.order_number }}",
                    "body": "Invoice {{ ctx.order_number }} is overdue."},
         "position": {"x": 200, "y": 0}},
        {"key": "end", "type": "end", "config": {}, "position": {"x": 400, "y": 0}},
    ]
    edges = [
        {"source": "start", "target": "notify", "ordering": 0, "condition": None},
        {"source": "notify", "target": "end", "ordering": 0, "condition": None},
    ]
    return {"nodes": nodes, "edges": edges, "trigger": None,
            "schedule": f"overdue_invoice:{params['days_overdue']}"}


def _new_lead_followup(params: dict) -> dict:
    nodes = [
        {"key": "start", "type": "start", "config": {}, "position": {"x": 0, "y": 0}},
        {"key": "notify", "type": "notification",
         "config": {"channel": "inapp", "recipient": "{{ ctx.owner }}",
                    "subject": "Follow up: {{ ctx.lead_name }}",
                    "body": "Lead {{ ctx.lead_name }} needs a follow-up."},
         "position": {"x": 200, "y": 0}},
        {"key": "end", "type": "end", "config": {}, "position": {"x": 400, "y": 0}},
    ]
    edges = [
        {"source": "start", "target": "notify", "ordering": 0, "condition": None},
        {"source": "notify", "target": "end", "ordering": 0, "condition": None},
    ]
    return {"nodes": nodes, "edges": edges, "trigger": None,
            "schedule": f"stale_lead:{params['days_since_created']}"}


def _ticket_escalation(params: dict) -> dict:
    # Escalation itself (priority bump + notify) already happens inside
    # erp.crm.services.support.escalate_ticket, which already publishes TICKET_ESCALATED and is
    # already handled by erp.notifications.handlers. This template's only job is to make the daily
    # sweep (Task 8) visible/toggleable as a workflow instead of a hidden hardcoded job — the
    # workflow itself is a no-op passthrough so it shows up in the Automations list and run history.
    nodes = [
        {"key": "start", "type": "start", "config": {}, "position": {"x": 0, "y": 0}},
        {"key": "end", "type": "end", "config": {}, "position": {"x": 200, "y": 0}},
    ]
    edges = [{"source": "start", "target": "end", "ordering": 0, "condition": None}]
    return {"nodes": nodes, "edges": edges, "trigger": None, "schedule": "ticket_escalation"}


_EXPANDERS = {
    "approval_above_amount": _approval_above_amount,
    "low_stock_alert": _low_stock_alert,
    "overdue_invoice_reminder": _overdue_invoice_reminder,
    "new_lead_followup": _new_lead_followup,
    "ticket_escalation": _ticket_escalation,
}


def expand(template_id: str, params: dict) -> dict:
    if template_id not in _EXPANDERS:
        raise ValidationError(f"unknown template: {template_id}")
    return _EXPANDERS[template_id](params)
