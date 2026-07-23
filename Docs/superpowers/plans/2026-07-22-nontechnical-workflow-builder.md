# Non-technical Workflow Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an SMB owner with no technical background build and understand ERP automations — five ready-made templates as the front door, a linear step-list editor as the escape hatch, zero JSON/graph literacy required.

**Architecture:** Pure additive layer on top of the existing workflow engine (`erp/workflow/engine`, unchanged). One new `NodeType.NOTIFICATION` + executor. One new `WorkflowTrigger` model that reuses the existing event bus (mirrors how Webhooks already subscribe to the same catalog) plus a small scheduled-check path for triggers that aren't a single discrete event. A `templates.py` service pure-function-expands a template id + params into the same `nodes`/`edges` shape the existing `services.save_graph()` already accepts — no new graph-persistence code. Frontend adds a template picker and a step-list builder as new pages; the existing React Flow canvas stays, demoted to an "Advanced" link.

**Tech Stack:** Django/DRF (backend, existing `erp/workflow` app), Celery beat (existing scheduled-task pattern from `erp/accounting/tasks.py`), React 18/TS (`apps/web`), existing `ComboBox` component, i18next (ar/en).

## Global Constraints

- Tokens only for colour — raw hex lives only in `apps/web/src/styles/tokens.css`.
- Logical CSS only (`inline-start/end`, never `left/right`) — RTL is the default.
- Every user-facing string is a key in BOTH `ar.json` and `en.json` — i18n parity is build-blocking (`node scripts/check-i18n-parity.mjs`).
- **No raw identifier ever shown to the user** — no event name (`crm.PR_SUBMITTED`), model field (`amount_minor`), or `NodeType` value (`api_call`) rendered directly, in either language (spec Section 6).
- Any string interpolating `{{count}}` must use i18next's CLDR plural suffixes (`_zero/_one/_two/_few/_many/_other`), not a hand-rolled ternary (per the 2026-07-22 fix, commit `ed1d9f4`) — this plan should not reintroduce that anti-pattern.
- No new frontend dependencies without asking — reuse `ComboBox`, `Popover`, existing toast/optimistic primitives.
- Money: integer minor units on the wire; format only at the edge (`apps/web/src/lib/money.ts`).
- Before "done" on any task: `npx tsc --noEmit` (or `-b`) and `node scripts/check-i18n-parity.mjs` from `apps/web`; `pytest erp/workflow erp/notifications erp/sales erp/inventory erp/crm -q` and `python scripts/gates/gate03.py` from repo root, as relevant to the files touched.

---

## File Structure

**Backend (`erp/workflow/`):**
- `executors/notification.py` — new: the "send a notification" node executor.
- `engine/registry.py` — modify: register the new executor.
- `models.py` — modify: `NodeType.NOTIFICATION`; new `WorkflowTrigger` model.
- `migrations/0005_notification_node_type.py`, `0006_workflowtrigger.py` — new.
- `triggers.py` — new: `WorkflowTrigger` CRUD + `on_domain_event` dispatcher (mirrors `notifications/services/webhooks.py::on_domain_event`).
- `trigger_catalog.py` — new: Arabic/English display-name map for triggerable events + condition fields (mirrors `notifications/webhook_catalog.py` but adds i18n labels instead of raw names).
- `templates.py` — new: the 5 template definitions as pure `expand(params) -> (nodes, edges, trigger)` functions + a `TEMPLATE_CATALOG` list.
- `tasks.py` — new: scheduled Celery tasks (low-stock check, overdue-invoice check, stale-lead check, daily ticket-escalation sweep).
- `views.py` — modify: add `TemplateCatalogView`, `TemplateCreateView`, `WorkflowTriggerListCreateView`.
- `urls.py` — modify: wire the three new views.
- `serializers.py` — modify: `TemplateCreateSerializer`, `WorkflowTriggerSerializer`.
- `apps.py` — modify: register the trigger dispatcher on ready (mirrors `notifications/apps.py`).

**Backend (other modules, additive only):**
- `erp/sales/domain/models.py` — modify: add `SalesOrder.due_date` (nullable date) for the overdue-invoice template.
- `erp/sales/migrations/00XX_salesorder_due_date.py` — new.
- `erp/sales/services/orders.py` — modify: set `due_date` at invoice time (find the existing invoice service call).
- `config/settings/base.py` — modify: register the new Celery beat entries.

**Frontend (`apps/web/src/`):**
- `pages/workflows/AutomationsPage.tsx` — new: template list + "start from scratch" entry (replaces `WorkflowListPage.tsx` as the default `/workflows` landing; canvas becomes `/workflows/advanced`).
- `pages/workflows/TemplateFormPage.tsx` — new: fill 2-4 fields for a chosen template, save.
- `pages/workflows/StepListBuilderPage.tsx` — new: the linear step-list editor.
- `pages/workflows/steps/` — new directory: `ApprovalStepForm.tsx`, `ConditionStepForm.tsx`, `NotificationStepForm.tsx` (assistant-action and api_call step forms reuse existing `NodeConfigPanel.tsx` sections, not duplicated).
- `api/workflowTemplates.ts` — new: typed client for the template/trigger endpoints.
- `i18n/locales/ar.json`, `en.json` — modify: new `automations.*` namespace.
- `pages/WorkflowNav.tsx` — modify: add "Automations" as the default tab, "Advanced" as the canvas tab.

---

### Task 1: Notification node type + executor

**Files:**
- Modify: `erp/workflow/models.py` (`NodeType` enum)
- Create: `erp/workflow/executors/notification.py`
- Modify: `erp/workflow/engine/registry.py`
- Create: `erp/workflow/migrations/0005_notification_node_type.py`
- Test: `erp/workflow/tests/test_notification_executor.py`

**Interfaces:**
- Produces: `NodeType.NOTIFICATION = "notification"`; `NotificationExecutor` (implements `NodeExecutor` protocol from `erp/workflow/engine/types.py`) — config keys `channel` (one of `NotificationChannel.choices`), `recipient`, `subject`, `body` (all three template strings, rendered via `erp.workflow.lib.template.render_value` against `node_input.instance_context`), `reference` (optional template string).

- [ ] **Step 1: Write the failing test**

```python
# erp/workflow/tests/test_notification_executor.py
from unittest.mock import patch

from erp.notifications.domain.models import NotificationChannel
from erp.workflow.engine.types import NodeInput
from erp.workflow.executors.notification import NotificationExecutor


def test_notification_executor_renders_templates_and_dispatches():
    executor = NotificationExecutor()
    node_input = NodeInput(
        instance_context={"owner": "ahmed", "ticket": "TKT-1"},
        node_config={
            "channel": "inapp",
            "recipient": "{{ ctx.owner }}",
            "subject": "Ticket {{ ctx.ticket }}",
            "body": "Ticket {{ ctx.ticket }} needs attention.",
        },
    )
    with patch("erp.notifications.services.dispatch") as mock_dispatch:
        output = executor.run(node_input)
    assert output.status == "success"
    mock_dispatch.assert_called_once_with(
        channel=NotificationChannel.INAPP,
        recipient="ahmed",
        subject="Ticket TKT-1",
        body="Ticket TKT-1 needs attention.",
        reference="",
        event_name="workflow.notification",
    )


def test_notification_executor_missing_recipient_fails_clearly():
    executor = NotificationExecutor()
    node_input = NodeInput(instance_context={}, node_config={"channel": "inapp", "subject": "x", "body": "y"})
    output = executor.run(node_input)
    assert output.status == "failed"
    assert "recipient" in (output.error or "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_notification_executor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'erp.workflow.executors.notification'`

- [ ] **Step 3: Add `NodeType.NOTIFICATION` to the model**

In `erp/workflow/models.py`, find `class NodeType(models.TextChoices):` and add one line after `SCRIPT = "script"`:

```python
    SCRIPT = "script"
    NOTIFICATION = "notification"
    END = "end"
```

- [ ] **Step 4: Write the executor**

```python
# erp/workflow/executors/notification.py
"""Notification node: send a message through the existing notifications dispatch service.

Config: channel, recipient, subject, body (all template strings rendered against instance
context — see erp.workflow.lib.template), optional reference. No new adapter — reuses
erp.notifications.services.dispatch exactly like other in-process module calls in this engine.
"""
from __future__ import annotations

from ..engine.types import NodeInput, NodeOutput
from ..lib.template import render_value


class NotificationExecutor:
    type = "notification"
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        from erp.notifications.domain.models import NotificationChannel
        from erp.notifications.services import dispatch

        cfg = node_input.node_config or {}
        try:
            recipient = render_value(cfg.get("recipient", ""), {"ctx": node_input.instance_context})
            subject = render_value(cfg.get("subject", ""), {"ctx": node_input.instance_context})
            body = render_value(cfg.get("body", ""), {"ctx": node_input.instance_context})
            reference = render_value(cfg.get("reference", ""), {"ctx": node_input.instance_context})
        except KeyError as exc:
            return NodeOutput(status="failed", output_payload={}, error=str(exc))

        if not recipient:
            return NodeOutput(status="failed", output_payload={},
                               error="This step has no recipient set.")

        channel = cfg.get("channel", NotificationChannel.INAPP)
        dispatch(
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            reference=reference,
            event_name="workflow.notification",
        )
        return NodeOutput(status="success", output_payload={"sent_to": recipient})
```

- [ ] **Step 5: Register the executor**

In `erp/workflow/engine/registry.py`, add the import and registry entry:

```python
from ..executors.notification import NotificationExecutor
```

```python
        NodeType.SCRIPT: ScriptExecutor(),
        NodeType.NOTIFICATION: NotificationExecutor(),
        NodeType.END: EndExecutor(),
```

- [ ] **Step 6: Generate and check the migration**

Run: `.venv/Scripts/python.exe manage.py makemigrations workflow --name notification_node_type`
Expected: creates `erp/workflow/migrations/0005_notification_node_type.py` with an `AlterField` on `WorkflowNode.type` adding `('notification', 'Notification')` to the choices list.

- [ ] **Step 7: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_notification_executor.py -v`
Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

```bash
git add erp/workflow/models.py erp/workflow/executors/notification.py erp/workflow/engine/registry.py erp/workflow/migrations/0005_notification_node_type.py erp/workflow/tests/test_notification_executor.py
git commit -m "feat(workflow): add notification node type + executor"
```

---

### Task 2: WorkflowTrigger model + event-bus dispatch

**Files:**
- Modify: `erp/workflow/models.py`
- Create: `erp/workflow/triggers.py`
- Create: `erp/workflow/migrations/0006_workflowtrigger.py`
- Modify: `erp/workflow/apps.py`
- Test: `erp/workflow/tests/test_triggers.py`

**Interfaces:**
- Consumes: `erp.core.events.bus` (`subscribe(event_name, handler)`, `publish`), `erp.notifications.webhook_catalog.WEBHOOK_EVENT_CATALOG` (list[str], the same event-name catalog), `erp.workflow.engine.engine.start_instance(workflow, payload, user=None)`.
- Produces: `WorkflowTrigger` model (`workflow` FK, `event_name` CharField, `condition` JSONField nullable, `is_active` BooleanField); `triggers.create_trigger(*, workflow_id, event_name, condition=None) -> WorkflowTrigger`; `triggers.on_domain_event(event) -> None` (subscribed to every catalog event name, mirrors `notifications.services.webhooks.on_domain_event`).

- [ ] **Step 1: Write the failing test**

```python
# erp/workflow/tests/test_triggers.py
import pytest

from erp.core.events import bus
from erp.workflow import triggers
from erp.workflow.models import InstanceStatus, Workflow, WorkflowInstance, WorkflowNode, WorkflowTrigger

pytestmark = pytest.mark.django_db


def _simple_workflow():
    wf = Workflow.objects.create(name="Notify on submit")
    start = WorkflowNode.objects.create(workflow=wf, key="start", type="start")
    end = WorkflowNode.objects.create(workflow=wf, key="end", type="end")
    from erp.workflow.models import WorkflowEdge

    WorkflowEdge.objects.create(workflow=wf, source=start, target=end, ordering=0)
    return wf


def test_trigger_starts_instance_on_matching_event():
    wf = _simple_workflow()
    triggers.create_trigger(workflow_id=wf.id, event_name="purchasing.PrSubmitted")

    bus.publish("purchasing.PrSubmitted", {"amount_minor": 10000})

    instance = WorkflowInstance.objects.get(workflow=wf)
    assert instance.status == InstanceStatus.COMPLETED
    assert instance.context["amount_minor"] == 10000


def test_trigger_condition_blocks_non_matching_event():
    wf = _simple_workflow()
    triggers.create_trigger(
        workflow_id=wf.id, event_name="purchasing.PrSubmitted",
        condition={">": [{"var": "amount_minor"}, 500000]},
    )

    bus.publish("purchasing.PrSubmitted", {"amount_minor": 10000})

    assert not WorkflowInstance.objects.filter(workflow=wf).exists()


def test_inactive_trigger_does_not_fire():
    wf = _simple_workflow()
    trigger = triggers.create_trigger(workflow_id=wf.id, event_name="purchasing.PrSubmitted")
    trigger.is_active = False
    trigger.save(update_fields=["is_active"])

    bus.publish("purchasing.PrSubmitted", {"amount_minor": 10000})

    assert not WorkflowInstance.objects.filter(workflow=wf).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_triggers.py -v`
Expected: FAIL with `ImportError: cannot import name 'triggers'` (module doesn't exist yet)

- [ ] **Step 3: Add the `WorkflowTrigger` model**

In `erp/workflow/models.py`, add after the `Workflow` class (before `WorkflowNode`):

```python
class WorkflowTrigger(models.Model):
    """Subscribes a workflow to a domain event, reusing the same event-name catalog Webhooks use.

    An optional JSON-logic `condition` gates the start (same shape/engine as edge conditions —
    see `erp.workflow.lib.jsonlogic`). No condition = fires on every occurrence of the event.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="triggers")
    event_name = models.CharField(max_length=64)
    condition = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_trigger"
        indexes = [models.Index(fields=["event_name", "is_active"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.workflow.name} on {self.event_name}"
```

(Remove the stray `id = uuid.uuid4` line above if pasted twice — the single `models.UUIDField` line is correct; this note exists so the implementer double-checks the file after editing rather than trusting a copy-paste blindly.)

- [ ] **Step 4: Write `triggers.py`**

```python
# erp/workflow/triggers.py
"""Workflow triggers: subscribe a workflow to a domain event, mirroring how Webhooks fan out
the same event catalog (`erp.notifications.services.webhooks.on_domain_event`). A trigger with
a condition only starts the workflow when the event payload matches — same JSON-logic engine
edges already use, so there's exactly one condition dialect in this codebase, not two.
"""
from __future__ import annotations

from erp.core.errors import NotFoundError, ValidationError
from erp.notifications.webhook_catalog import WEBHOOK_EVENT_CATALOG

from .engine import engine
from .lib.jsonlogic import jsonlogic
from .models import Workflow, WorkflowTrigger


def create_trigger(*, workflow_id, event_name: str, condition: dict | None = None) -> WorkflowTrigger:
    if event_name not in WEBHOOK_EVENT_CATALOG:
        raise ValidationError(f"unknown event: {event_name}")
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist as exc:
        raise NotFoundError("workflow not found") from exc
    return WorkflowTrigger.objects.create(
        workflow=workflow, event_name=event_name, condition=condition,
    )


def on_domain_event(event) -> None:
    """Core-event listener: start every active, matching trigger's workflow."""
    triggers = WorkflowTrigger.objects.filter(
        is_active=True, event_name=event.name,
    ).select_related("workflow")
    for trigger in triggers:
        if trigger.condition and not jsonlogic(trigger.condition, event.payload):
            continue
        engine.start_instance(trigger.workflow, event.payload)
```

- [ ] **Step 5: Wire the bus subscription in `apps.py`**

Read `erp/workflow/apps.py` first to see its current `ready()` (if any); add a `ready()` method following the exact pattern in `erp/notifications/apps.py`:

```python
    def ready(self) -> None:
        from erp.notifications.webhook_catalog import WEBHOOK_EVENT_CATALOG
        from erp.core.events import bus

        from . import triggers

        for _name in WEBHOOK_EVENT_CATALOG:
            bus.subscribe(_name, triggers.on_domain_event)
```

If `WorkflowConfig.ready()` already does something else, add these lines to the existing method rather than replacing it.

- [ ] **Step 6: Generate the migration**

Run: `.venv/Scripts/python.exe manage.py makemigrations workflow --name workflowtrigger`
Expected: creates `erp/workflow/migrations/0006_workflowtrigger.py` with a `CreateModel` for `WorkflowTrigger`.

- [ ] **Step 7: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_triggers.py -v`
Expected: PASS (3 tests). Note: `engine.start_instance` runs the instance synchronously to completion for a trivial start→end graph, so `test_trigger_starts_instance_on_matching_event` can assert `COMPLETED` directly without polling.

- [ ] **Step 8: Commit**

```bash
git add erp/workflow/models.py erp/workflow/triggers.py erp/workflow/apps.py erp/workflow/migrations/0006_workflowtrigger.py erp/workflow/tests/test_triggers.py
git commit -m "feat(workflow): add WorkflowTrigger — event-bus-driven workflow starts"
```

---

### Task 3: Trigger + condition-field Arabic/English display catalog

**Files:**
- Create: `erp/workflow/trigger_catalog.py`
- Test: `erp/workflow/tests/test_trigger_catalog.py`

**Interfaces:**
- Consumes: `erp.notifications.webhook_catalog.WEBHOOK_EVENT_CATALOG`.
- Produces: `TRIGGER_DISPLAY: dict[str, dict[str, str]]` — `{event_name: {"ar": "...", "en": "..."}}`, covering every entry the templates in Task 6 use; `TRIGGER_FIELDS: dict[str, list[dict]]` — `{event_name: [{"field": "amount_minor", "label": {"ar": "...", "en": "..."}}]}` for the condition-builder ComboBox (spec Section 6 — never show a raw field key).

- [ ] **Step 1: Write the failing test**

```python
# erp/workflow/tests/test_trigger_catalog.py
from erp.workflow.trigger_catalog import TRIGGER_DISPLAY, TRIGGER_FIELDS


def test_every_used_trigger_has_both_language_labels():
    used_events = ["purchasing.PrSubmitted", "sales.OrderConfirmed"]
    for name in used_events:
        assert name in TRIGGER_DISPLAY, f"missing display entry for {name}"
        assert TRIGGER_DISPLAY[name]["ar"], f"missing Arabic label for {name}"
        assert TRIGGER_DISPLAY[name]["en"], f"missing English label for {name}"


def test_trigger_fields_have_both_language_labels():
    fields = TRIGGER_FIELDS.get("purchasing.PrSubmitted", [])
    assert fields, "purchasing.PrSubmitted needs at least one condition field"
    for f in fields:
        assert f["label"]["ar"] and f["label"]["en"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_trigger_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'erp.workflow.trigger_catalog'`

- [ ] **Step 3: Confirm the real event names before writing the catalog**

Run: `.venv/Scripts/python.exe manage.py shell -c "from erp.purchasing import events; from erp.sales import events as se; print(events.PR_SUBMITTED); print(se.ORDER_CONFIRMED)"`
Expected: prints the two exact event-name strings — use these literal values in the dict below, do not guess at naming.

- [ ] **Step 4: Write the catalog**

```python
# erp/workflow/trigger_catalog.py
"""Arabic/English display names for triggerable events and their condition fields.

The event bus and WEBHOOK_EVENT_CATALOG deal in raw names (e.g. "purchasing.PrSubmitted");
this module is the only place those names are mapped to what a non-technical user actually
sees. Nothing outside erp/workflow (and the API views that expose these maps) should render a
raw event name or payload field key to an end user — see spec Section 6.
"""
from __future__ import annotations

from erp.purchasing.events import PR_SUBMITTED, PO_APPROVED
from erp.sales.events import ORDER_CONFIRMED

TRIGGER_DISPLAY: dict[str, dict[str, str]] = {
    PR_SUBMITTED: {"ar": "عند إرسال طلب شراء", "en": "When a purchase request is submitted"},
    PO_APPROVED: {"ar": "عند الموافقة على أمر شراء", "en": "When a purchase order is approved"},
    ORDER_CONFIRMED: {"ar": "عند تأكيد طلب بيع", "en": "When a sales order is confirmed"},
}

TRIGGER_FIELDS: dict[str, list[dict]] = {
    PR_SUBMITTED: [
        {"field": "amount_minor", "label": {"ar": "الإجمالي", "en": "Total amount"}},
    ],
    PO_APPROVED: [
        {"field": "amount_minor", "label": {"ar": "الإجمالي", "en": "Total amount"}},
    ],
    ORDER_CONFIRMED: [
        {"field": "amount_minor", "label": {"ar": "الإجمالي", "en": "Total amount"}},
    ],
}
```

Use the exact event-name string values printed in Step 3 as the imports — if the real import path differs from `erp.purchasing.events.PR_SUBMITTED` / `erp.sales.events.ORDER_CONFIRMED`, correct the import lines to match, keeping the dict keys as those same string values either way.

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_trigger_catalog.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add erp/workflow/trigger_catalog.py erp/workflow/tests/test_trigger_catalog.py
git commit -m "feat(workflow): Arabic/English display catalog for triggers + condition fields"
```

---

### Task 4: SalesOrder due date (for the overdue-invoice template)

**Files:**
- Modify: `erp/sales/domain/models.py`
- Modify: `erp/sales/services/orders.py`
- Create: `erp/sales/migrations/00XX_salesorder_due_date.py` (exact number = next after the highest existing migration in `erp/sales/migrations/`)
- Test: `erp/sales/tests/test_orders.py` (add to existing file, do not create a new one — check it exists first)

**Interfaces:**
- Produces: `SalesOrder.due_date` (nullable `DateField`), set by `orders.invoice_order(...)` to `order_date + timedelta(days=payment_terms_days)` where `payment_terms_days` is a new keyword argument defaulting to `30`.

- [ ] **Step 1: Find the exact invoicing call site**

Run: `.venv/Scripts/python.exe -c "import subprocess; print(subprocess.run(['grep', '-n', 'def invoice_order', 'erp/sales/services/orders.py'], capture_output=True, text=True).stdout)"`

Read the surrounding 30 lines of `erp/sales/services/orders.py` around that line number before writing Step 4 — this plan cannot show the exact existing function body sight-unseen; the implementer must open the file, find where `order.invoiced_minor` and `order.status` are set inside `invoice_order`, and add the `due_date` assignment in the same block, following the same `update_fields=[...]` pattern already used there.

- [ ] **Step 2: Write the failing test**

Add to `erp/sales/tests/test_orders.py` (append, matching the existing test style/fixtures in that file — read the top of the file for its fixture helpers first):

```python
def test_invoice_order_sets_due_date_30_days_out(confirmed_order):
    invoiced = invoice_order(confirmed_order.id)
    assert invoiced.due_date == invoiced.order_date + timedelta(days=30)
```

(If the file's existing tests don't use a `confirmed_order` fixture, use whichever fixture/helper the file's other `invoice_order` tests already use — do not invent a new one.)

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest erp/sales/tests/test_orders.py -k due_date -v`
Expected: FAIL with `AttributeError: 'SalesOrder' object has no attribute 'due_date'`

- [ ] **Step 4: Add the field**

In `erp/sales/domain/models.py`, in `class SalesOrder(AuditedModel):`, add after `invoice_number`:

```python
    invoice_number = models.CharField(max_length=32, blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
```

- [ ] **Step 5: Set it in `invoice_order`**

Following the exact function found in Step 1, add (inside the same transaction, alongside the existing status/amount updates):

```python
from datetime import timedelta
# ... inside invoice_order, before the .save(update_fields=[...]) call:
order.due_date = order.order_date + timedelta(days=payment_terms_days)
```

Add `payment_terms_days: int = 30` as a keyword parameter on `invoice_order`'s signature, and add `"due_date"` to that same `update_fields` list.

- [ ] **Step 6: Generate the migration**

Run: `.venv/Scripts/python.exe manage.py makemigrations sales --name salesorder_due_date`
Expected: creates the migration adding `due_date` to `SalesOrder`.

- [ ] **Step 7: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest erp/sales/tests/test_orders.py -k due_date -v`
Expected: PASS

- [ ] **Step 8: Run the full sales suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest erp/sales -q`
Expected: all pass (the new field is nullable and additive — no existing test should touch it)

- [ ] **Step 9: Commit**

```bash
git add erp/sales/domain/models.py erp/sales/services/orders.py erp/sales/migrations/ erp/sales/tests/test_orders.py
git commit -m "feat(sales): add SalesOrder.due_date, set at invoicing (30-day default term)"
```

---

### Task 5: Template registry (5 templates as pure expansion functions)

**Files:**
- Create: `erp/workflow/templates.py`
- Test: `erp/workflow/tests/test_templates.py`

**Interfaces:**
- Consumes: `NodeType` (Task 1), `WorkflowTrigger` shape (Task 2), `TRIGGER_DISPLAY`/`TRIGGER_FIELDS` (Task 3).
- Produces: `TEMPLATE_CATALOG: list[dict]` — each `{"id": str, "name": {"ar": str, "en": str}, "fields": list[dict]}` (fields = what the template form asks for, e.g. `{"key": "amount_minor", "type": "money", "label": {...}}`); `expand(template_id: str, params: dict) -> dict` returning `{"nodes": [...], "edges": [...], "trigger": {"event_name": str, "condition": dict | None} | None, "schedule": str | None}` in exactly the shape `services.save_graph()` and `triggers.create_trigger()` already accept.

- [ ] **Step 1: Write the failing test**

```python
# erp/workflow/tests/test_templates.py
from erp.workflow.templates import TEMPLATE_CATALOG, expand


def test_catalog_has_five_templates():
    ids = {t["id"] for t in TEMPLATE_CATALOG}
    assert ids == {
        "approval_above_amount", "low_stock_alert", "overdue_invoice_reminder",
        "new_lead_followup", "ticket_escalation",
    }


def test_approval_above_amount_expands_to_a_valid_graph():
    result = expand("approval_above_amount", {
        "amount_minor": 500000, "approver_role": "finance_manager",
    })
    node_keys = {n["key"] for n in result["nodes"]}
    assert node_keys == {"start", "check_amount", "ask_approval", "end"}
    condition_node = next(n for n in result["nodes"] if n["key"] == "check_amount")
    assert condition_node["type"] == "condition"
    approval_node = next(n for n in result["nodes"] if n["key"] == "ask_approval")
    assert approval_node["config"]["approver_role"] == "finance_manager"
    assert result["trigger"]["condition"] == {">": [{"var": "amount_minor"}, 500000]}


def test_unknown_template_raises():
    import pytest
    from erp.core.errors import ValidationError

    with pytest.raises(ValidationError):
        expand("not_a_real_template", {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_templates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'erp.workflow.templates'`

- [ ] **Step 3: Write the template registry**

```python
# erp/workflow/templates.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_templates.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add erp/workflow/templates.py erp/workflow/tests/test_templates.py
git commit -m "feat(workflow): template registry — 5 fixed automation recipes"
```

---

### Task 6: Template + trigger API endpoints

**Files:**
- Modify: `erp/workflow/serializers.py`
- Modify: `erp/workflow/views.py`
- Modify: `erp/workflow/urls.py`
- Test: `erp/workflow/tests/test_template_api.py`

**Interfaces:**
- Consumes: `templates.TEMPLATE_CATALOG`, `templates.expand()` (Task 5); `services.save_graph()` (existing); `triggers.create_trigger()` (Task 2).
- Produces: `GET /api/workflows/templates` → `TEMPLATE_CATALOG`; `POST /api/workflows/templates/<id>` (body: `{"name": str, "params": dict}`) → creates the workflow (+ trigger if the template has one) and returns the same envelope shape as `WorkflowListCreateView.post`.

- [ ] **Step 1: Write the failing test**

```python
# erp/workflow/tests/test_template_api.py
import pytest
from rest_framework.test import APIClient

from erp.workflow.models import Workflow, WorkflowTrigger

pytestmark = pytest.mark.django_db


def test_template_catalog_endpoint(authed_client: APIClient):
    resp = authed_client.get("/api/workflows/templates")
    assert resp.status_code == 200
    ids = {t["id"] for t in resp.json()["data"]}
    assert "approval_above_amount" in ids


def test_create_from_template_creates_workflow_and_trigger(authed_client: APIClient):
    resp = authed_client.post(
        "/api/workflows/templates/approval_above_amount",
        {"name": "PO approvals over 5000", "params": {"amount_minor": 500000, "approver_role": "finance_manager"}},
        format="json",
    )
    assert resp.status_code == 201
    wf = Workflow.objects.get(name="PO approvals over 5000")
    assert wf.nodes.count() == 4
    assert WorkflowTrigger.objects.filter(workflow=wf).exists()
```

(If the test suite doesn't already have an `authed_client` fixture, check `erp/workflow/tests/conftest.py` or the repo-root `conftest.py` for the existing authenticated-client fixture name used by `test_template_api.py`'s sibling tests such as `views.py`'s other endpoint tests, and use that exact fixture name instead.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_template_api.py -v`
Expected: FAIL with 404 (route doesn't exist yet)

- [ ] **Step 3: Add serializers**

In `erp/workflow/serializers.py`, add:

```python
class TemplateCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    params = serializers.DictField()
```

- [ ] **Step 4: Add the views**

In `erp/workflow/views.py`, add:

```python
from . import templates, triggers


class TemplateCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope(templates.TEMPLATE_CATALOG)


class TemplateCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, template_id: str) -> Response:
        s = TemplateCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        graph = templates.expand(template_id, s.validated_data["params"])
        wf = services.save_graph(
            name=s.validated_data["name"], nodes=graph["nodes"], edges=graph["edges"],
        )
        if graph["trigger"]:
            triggers.create_trigger(
                workflow_id=wf.id,
                event_name=graph["trigger"]["event_name"],
                condition=graph["trigger"].get("condition"),
            )
        return _envelope(WorkflowGraphSerializer(wf).data, status=201)
```

Add `TemplateCreateSerializer` to the existing `from .serializers import (...)` block at the top of `views.py`.

- [ ] **Step 5: Wire the routes**

In `erp/workflow/urls.py`, add before the `workflows/<uuid:workflow_id>` line (more specific paths first):

```python
    path("workflows/templates", views.TemplateCatalogView.as_view(), name="template-catalog"),
    path("workflows/templates/<str:template_id>", views.TemplateCreateView.as_view(), name="template-create"),
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_template_api.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Run the full workflow suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow -q`
Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add erp/workflow/serializers.py erp/workflow/views.py erp/workflow/urls.py erp/workflow/tests/test_template_api.py
git commit -m "feat(workflow): template catalog + create-from-template API"
```

---

### Task 7: Scheduled triggers (low stock, overdue invoice, stale lead, ticket escalation)

**Files:**
- Create: `erp/workflow/tasks.py`
- Modify: `config/settings/base.py`
- Modify: `erp/workflow/models.py` (extend `WorkflowTrigger` with a `schedule` field — see Step 3)
- Create: `erp/workflow/migrations/0007_workflowtrigger_schedule.py`
- Test: `erp/workflow/tests/test_scheduled_triggers.py`

**Interfaces:**
- Consumes: `WorkflowTrigger` (extended), `engine.start_instance`, `erp.inventory.domain.models.StockBalance`/`Item`, `erp.sales.domain.models.SalesOrder` (Task 4's `due_date`), `erp.crm.domain.models.Lead`, `erp.crm.services.support.run_escalations`.
- Produces: `erp.workflow.tasks.run_scheduled_triggers()` (Celery task, name `"workflow.run_scheduled_triggers"`) — one shared task that dispatches to per-`schedule`-value checker functions; four checker functions: `_check_low_stock()`, `_check_overdue_invoices(days)`, `_check_stale_leads(days)`, `_check_ticket_escalations()`.

- [ ] **Step 1: Write the failing test**

```python
# erp/workflow/tests/test_scheduled_triggers.py
import pytest
from django.utils import timezone
from datetime import timedelta

from erp.workflow.models import InstanceStatus, Workflow, WorkflowInstance, WorkflowNode, WorkflowEdge, WorkflowTrigger
from erp.workflow.tasks import run_scheduled_triggers

pytestmark = pytest.mark.django_db


def _notify_workflow():
    wf = Workflow.objects.create(name="Low stock alert")
    start = WorkflowNode.objects.create(workflow=wf, key="start", type="start")
    end = WorkflowNode.objects.create(workflow=wf, key="end", type="end")
    WorkflowEdge.objects.create(workflow=wf, source=start, target=end, ordering=0)
    return wf


def test_low_stock_schedule_starts_one_instance_per_low_item(item_below_reorder_point):
    wf = _notify_workflow()
    WorkflowTrigger.objects.create(workflow=wf, event_name="", schedule="low_stock", is_active=True)

    run_scheduled_triggers()

    instance = WorkflowInstance.objects.get(workflow=wf)
    assert instance.status == InstanceStatus.COMPLETED
    assert instance.context["item_name"] == item_below_reorder_point.name
```

(`item_below_reorder_point` must be a new fixture in `erp/workflow/tests/conftest.py` — check whether inventory fixtures for `Item`/`StockBalance`/`Warehouse` already exist in `erp/inventory/tests/conftest.py` and reuse that factory pattern rather than inventing a new one from scratch.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_scheduled_triggers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'erp.workflow.tasks'`

- [ ] **Step 3: Extend `WorkflowTrigger` with `schedule`**

In `erp/workflow/models.py`, on `WorkflowTrigger`, make `event_name` allow blank and add a new field:

```python
    event_name = models.CharField(max_length=64, blank=True, default="")
    condition = models.JSONField(null=True, blank=True)
    schedule = models.CharField(max_length=64, blank=True, default="")  # e.g. "low_stock", "overdue_invoice:7"
    is_active = models.BooleanField(default=True)
```

Run: `.venv/Scripts/python.exe manage.py makemigrations workflow --name workflowtrigger_schedule`

- [ ] **Step 3b: Extend `create_trigger` and `TemplateCreateView` for schedule-based templates**

Task 6's `TemplateCreateView` only ever created an event trigger (`graph["trigger"]`) — the four
schedule-based templates (`low_stock_alert`, `overdue_invoice_reminder`, `new_lead_followup`,
`ticket_escalation`) set `graph["schedule"]` instead, and without this step their generated
workflow would have no `WorkflowTrigger` row at all, so `run_scheduled_triggers` (Step 4 below)
would never find and run them. Fix both places now that `schedule` exists on the model.

In `erp/workflow/triggers.py`, change `create_trigger`'s signature and body:

```python
def create_trigger(
    *, workflow_id, event_name: str = "", condition: dict | None = None, schedule: str = "",
) -> WorkflowTrigger:
    if event_name and event_name not in WEBHOOK_EVENT_CATALOG:
        raise ValidationError(f"unknown event: {event_name}")
    if not event_name and not schedule:
        raise ValidationError("a trigger needs either an event_name or a schedule")
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist as exc:
        raise NotFoundError("workflow not found") from exc
    return WorkflowTrigger.objects.create(
        workflow=workflow, event_name=event_name, condition=condition, schedule=schedule,
    )
```

In `erp/workflow/views.py`, `TemplateCreateView.post`, replace the trigger-creation block:

```python
        if graph["trigger"]:
            triggers.create_trigger(
                workflow_id=wf.id,
                event_name=graph["trigger"]["event_name"],
                condition=graph["trigger"].get("condition"),
            )
        elif graph.get("schedule"):
            triggers.create_trigger(workflow_id=wf.id, schedule=graph["schedule"])
```

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_triggers.py erp/workflow/tests/test_template_api.py -v`
Expected: still PASS (existing tests only exercise the event-trigger path, which is unchanged in behavior).

- [ ] **Step 4: Write the scheduled task module**

```python
# erp/workflow/tasks.py
"""Celery tasks for scheduled (non-event) workflow triggers — low stock, overdue invoices, stale
leads, ticket escalation. Mirrors erp/accounting/tasks.py's single-purpose @shared_task pattern;
the beat schedule (config/settings/base.py CELERY_BEAT_SCHEDULE) fires this once daily and this
task decides what's due, same shape as `accounting.run_scheduled_reports`.
"""
from __future__ import annotations

from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

from .engine import engine
from .models import WorkflowTrigger


def _check_low_stock() -> None:
    from erp.inventory.domain.models import Item, StockBalance

    for item in Item.objects.filter(reorder_point__gt=0):
        on_hand = StockBalance.objects.filter(item=item).aggregate(total=Sum("quantity"))["total"] or 0
        if on_hand < item.reorder_point:
            for trigger in WorkflowTrigger.objects.filter(schedule="low_stock", is_active=True):
                engine.start_instance(trigger.workflow, {"item_name": item.name, "on_hand": float(on_hand)})


def _check_overdue_invoices(days: int) -> None:
    from erp.sales.domain.models import OrderStatus, SalesOrder

    cutoff = timezone.now().date() - timezone.timedelta(days=days)
    # outstanding_minor is a Python property (invoiced_minor - paid_minor), not a queryable field,
    # so the outstanding>0 filter runs in Python after the DB narrows by status/due_date.
    candidates = SalesOrder.objects.filter(status=OrderStatus.INVOICED, due_date__lt=cutoff)
    overdue = [o for o in candidates if o.outstanding_minor > 0]
    for order in overdue:
        for trigger in WorkflowTrigger.objects.filter(schedule=f"overdue_invoice:{days}", is_active=True):
            engine.start_instance(trigger.workflow, {"order_number": order.number})


def _check_stale_leads(days: int) -> None:
    from erp.crm.domain.models import Lead, LeadStatus

    cutoff = timezone.now() - timezone.timedelta(days=days)
    stale = Lead.objects.filter(status=LeadStatus.NEW, created_at__lt=cutoff)
    for lead in stale:
        for trigger in WorkflowTrigger.objects.filter(schedule=f"stale_lead:{days}", is_active=True):
            engine.start_instance(trigger.workflow, {"lead_name": lead.name, "owner": lead.owner})


def _check_ticket_escalations() -> None:
    from erp.crm.services.support import run_escalations

    escalated = run_escalations()
    if escalated:
        for trigger in WorkflowTrigger.objects.filter(schedule="ticket_escalation", is_active=True):
            engine.start_instance(trigger.workflow, {"escalated_count": len(escalated)})


@shared_task(name="workflow.run_scheduled_triggers")
def run_scheduled_triggers() -> None:
    """Run every scheduled-trigger check once. Each checker is independently idempotent (matches
    the existing `run_escalations` guard pattern) — running this twice in a row is always safe."""
    _check_low_stock()
    _check_ticket_escalations()
    for trigger in WorkflowTrigger.objects.filter(is_active=True).exclude(schedule=""):
        if trigger.schedule.startswith("overdue_invoice:"):
            _check_overdue_invoices(int(trigger.schedule.split(":")[1]))
        elif trigger.schedule.startswith("stale_lead:"):
            _check_stale_leads(int(trigger.schedule.split(":")[1]))
```

- [ ] **Step 5: Register the beat schedule**

In `config/settings/base.py`, inside `CELERY_BEAT_SCHEDULE`, add:

```python
    "run-scheduled-workflow-triggers": {
        "task": "workflow.run_scheduled_triggers",
        "schedule": crontab(hour=7, minute=15),  # 07:15 Africa/Cairo daily
    },
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow/tests/test_scheduled_triggers.py -v`
Expected: PASS

- [ ] **Step 7: Run the full workflow + crm + inventory + sales suites**

Run: `.venv/Scripts/python.exe -m pytest erp/workflow erp/crm erp/inventory erp/sales -q`
Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add erp/workflow/models.py erp/workflow/migrations/ erp/workflow/tasks.py config/settings/base.py erp/workflow/tests/test_scheduled_triggers.py
git commit -m "feat(workflow): scheduled triggers — low stock, overdue invoices, stale leads, ticket escalation"
```

---

### Task 8: i18n — automations namespace (Arabic + English)

**Files:**
- Modify: `apps/web/src/i18n/locales/ar.json`
- Modify: `apps/web/src/i18n/locales/en.json`

**Interfaces:**
- Produces: an `automations` top-level key covering everything Tasks 9-12's components reference: `automations.title`, `automations.subtitle`, `automations.templatesHeading`, `automations.startFromScratch`, `automations.advanced`, `automations.template.<id>.name` (mirrors `templates.py`'s `name` field per template — kept in sync manually since the backend already returns the localized name directly in its API response, so the frontend never needs its own copy of template names; this section is for everything else: form field labels, step-list chrome), `automations.field.amount`, `automations.field.approverRole`, `automations.field.recipient`, `automations.field.daysOverdue`, `automations.field.daysSinceCreated`, `automations.save`, `automations.saved`, `automations.steps.when`, `automations.steps.do`, `automations.steps.if`, `automations.steps.otherwise`, `automations.steps.addStep`, `automations.steps.type.approval`, `automations.steps.type.notification`, `automations.steps.type.condition`, `automations.steps.type.assistant`, `automations.steps.type.apiCall`.

- [ ] **Step 1: Add the English keys**

In `apps/web/src/i18n/locales/en.json`, add a new top-level `"automations"` object (find the alphabetically/logically nearest existing top-level key such as `"assistant"` or `"canvas"` and insert nearby, matching the file's existing style of one top-level key per feature area):

```json
  "automations": {
    "title": "Automations",
    "subtitle": "Automations that run themselves, in plain language.",
    "templatesHeading": "Start from a template",
    "startFromScratch": "Start from scratch",
    "advanced": "Advanced (workflow canvas)",
    "field": {
      "amount": "Amount",
      "approverRole": "Who approves",
      "recipient": "Who to notify",
      "daysOverdue": "Days overdue",
      "daysSinceCreated": "After how many days"
    },
    "save": "Save",
    "saved": "Automation saved",
    "steps": {
      "when": "When",
      "do": "Do",
      "if": "If",
      "otherwise": "Otherwise",
      "addStep": "Add a step",
      "type": {
        "approval": "Ask someone to approve",
        "notification": "Send a notification",
        "condition": "Check a condition",
        "assistant": "Let the assistant draft something",
        "apiCall": "Call another system"
      }
    }
  },
```

- [ ] **Step 2: Add the matching Arabic keys**

In `apps/web/src/i18n/locales/ar.json`, at the same structural position (find the `"canvas"`/`"assistant"` key in `ar.json` to match where you inserted in `en.json`):

```json
  "automations": {
    "title": "الأتمتة",
    "subtitle": "أتمتة تعمل من تلقاء نفسها، بلغة بسيطة.",
    "templatesHeading": "ابدأ من قالب جاهز",
    "startFromScratch": "ابدأ من الصفر",
    "advanced": "متقدم (محرر مسارات العمل)",
    "field": {
      "amount": "المبلغ",
      "approverRole": "من يوافق",
      "recipient": "من يُخطَر",
      "daysOverdue": "عدد أيام التأخير",
      "daysSinceCreated": "بعد كم يوم"
    },
    "save": "حفظ",
    "saved": "تم حفظ الأتمتة",
    "steps": {
      "when": "عند",
      "do": "قم بـ",
      "if": "إذا",
      "otherwise": "وإلا",
      "addStep": "أضف خطوة",
      "type": {
        "approval": "اطلب موافقة أحدهم",
        "notification": "أرسل إشعارًا",
        "condition": "تحقق من شرط",
        "assistant": "دع المساعد يُعِدّ مسودة",
        "apiCall": "استدعِ نظامًا آخر"
      }
    }
  },
```

- [ ] **Step 3: Run the parity check**

Run: `cd apps/web && node scripts/check-i18n-parity.mjs`
Expected: `i18n parity OK` (key count increases by the same amount in both files since they were added together)

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/i18n/locales/ar.json apps/web/src/i18n/locales/en.json
git commit -m "feat(i18n): automations namespace (ar+en)"
```

---

### Task 9: Frontend API client for templates + triggers

**Files:**
- Create: `apps/web/src/api/workflowTemplates.ts`
- Test: none required (thin typed fetch wrapper, matches the existing `api/workflows.ts` pattern with no independent logic to unit test — same convention as other `api/*.ts` files in this codebase)

**Interfaces:**
- Consumes: whatever the existing `api/workflows.ts` uses for its base request helper (open that file first and reuse its imported helper — e.g. `apiGet`/`apiPost` — rather than reinventing fetch logic).
- Produces: `export interface WorkflowTemplate { id: string; name: { ar: string; en: string }; fields: TemplateField[] }`, `export interface TemplateField { key: string; type: string; label: { ar: string; en: string } }`, `listTemplates(): Promise<WorkflowTemplate[]>`, `createFromTemplate(templateId: string, name: string, params: Record<string, unknown>): Promise<WorkflowGraph>` (reuse the existing `WorkflowGraph` type from `api/types.ts` if one exists — check before defining a new one).

- [ ] **Step 1: Read the existing pattern**

Open `apps/web/src/api/workflows.ts` in full — note its import of the shared request helper, its base URL prefix, and its existing `WorkflowGraph`-shaped type (if present in `api/types.ts`) before writing Step 2.

- [ ] **Step 2: Write the client**

```typescript
// apps/web/src/api/workflowTemplates.ts
import { apiGet, apiPost } from "./client"; // adjust to the exact helper names found in workflows.ts
import type { WorkflowGraph } from "./types"; // adjust if the existing type has a different name

export interface TemplateField {
  key: string;
  type: string;
  label: { ar: string; en: string };
}

export interface WorkflowTemplate {
  id: string;
  name: { ar: string; en: string };
  fields: TemplateField[];
}

export function listTemplates(): Promise<WorkflowTemplate[]> {
  return apiGet<WorkflowTemplate[]>("/workflows/templates");
}

export function createFromTemplate(
  templateId: string,
  name: string,
  params: Record<string, unknown>,
): Promise<WorkflowGraph> {
  return apiPost<WorkflowGraph>(`/workflows/templates/${templateId}`, { name, params });
}
```

Correct the import names/paths in this step to match exactly what Step 1 found — do not guess at `apiGet`/`apiPost`/`WorkflowGraph` if the real names differ.

- [ ] **Step 3: Type-check**

Run: `cd apps/web && npx tsc -b`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/api/workflowTemplates.ts
git commit -m "feat(workflow): frontend API client for templates"
```

---

### Task 10: Automations page — template picker

**Files:**
- Create: `apps/web/src/pages/workflows/AutomationsPage.tsx`
- Create: `apps/web/src/pages/workflows/AutomationsPage.css`
- Create: `apps/web/src/pages/workflows/TemplateFormPage.tsx`
- Modify: whatever router file wires `/workflows` (find it by grepping the router for `WorkflowListPage` first)
- Test: none at this layer (covered end-to-end by Task 14's E2E test)

**Interfaces:**
- Consumes: `listTemplates()`, `createFromTemplate()` (Task 9); `ComboBox` (for the `role`/`person` field types); existing toast (`useToast` — check `api/workflowTemplates.ts`'s sibling pages for the exact hook name/import path).
- Produces: `/workflows` renders `AutomationsPage` (template grid + "start from scratch" link to the step-list builder + "Advanced" link to the existing canvas); `/workflows/templates/:templateId` renders `TemplateFormPage` (dynamic form from the template's `fields`, submit → `createFromTemplate` → toast → navigate to the new workflow's detail).

- [ ] **Step 1: Find the router wiring**

Run: `cd apps/web/src && grep -rn "WorkflowListPage" .`

Read the matched route file to see the exact route-registration pattern (React Router v6 `<Route>` JSX, or a route config object — match whichever this codebase uses) before writing Step 3.

- [ ] **Step 2: Write `AutomationsPage.tsx`**

```tsx
// apps/web/src/pages/workflows/AutomationsPage.tsx
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { listTemplates, type WorkflowTemplate } from "../../api/workflowTemplates";
import "./AutomationsPage.css";

export function AutomationsPage() {
  const { t, i18n } = useTranslation();
  const { data, loading, error, reload } = useAsync<WorkflowTemplate[]>(() => listTemplates(), []);

  return (
    <section className="automations">
      <h1>{t("automations.title")}</h1>
      <p className="muted">{t("automations.subtitle")}</p>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <h2>{t("automations.templatesHeading")}</h2>
          <div className="automations__grid">
            {data.map((tpl) => (
              <Link key={tpl.id} to={`/workflows/templates/${tpl.id}`} className="card automations__card">
                {tpl.name[i18n.language as "ar" | "en"] ?? tpl.name.en}
              </Link>
            ))}
          </div>
        </>
      )}

      <div className="automations__footer">
        <Link to="/workflows/build">{t("automations.startFromScratch")}</Link>
        <Link to="/workflows/advanced">{t("automations.advanced")}</Link>
      </div>
    </section>
  );
}
```

Adjust the `useAsync`/`ErrorState`/`ListSkeleton` import paths to match this codebase's actual locations (confirmed already correct per `ExecutionViewerPage.tsx`'s identical imports, reused here for consistency).

- [ ] **Step 3: Write `AutomationsPage.css`**

```css
.automations__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: var(--space-3);
  margin-block-end: var(--space-4);
}

.automations__card {
  display: block;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background-color: var(--color-surface-alt);
  text-decoration: none;
  color: var(--color-text);
}

.automations__footer {
  display: flex;
  gap: var(--space-3);
}
```

- [ ] **Step 4: Write `TemplateFormPage.tsx`**

```tsx
// apps/web/src/pages/workflows/TemplateFormPage.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { listTemplates, createFromTemplate, type WorkflowTemplate } from "../../api/workflowTemplates";

export function TemplateFormPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const { data: templates, loading } = useAsync<WorkflowTemplate[]>(() => listTemplates(), []);
  const template = templates?.find((tpl) => tpl.id === templateId);
  const [name, setName] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  if (loading || !template) return null;

  async function onSave() {
    setSaving(true);
    try {
      const params: Record<string, unknown> = {};
      for (const field of template!.fields) {
        params[field.key] = field.type === "money" || field.type === "number"
          ? Number(values[field.key] ?? 0)
          : values[field.key] ?? "";
      }
      const wf = await createFromTemplate(templateId as string, name, params);
      toast.show(t("automations.saved"), "success");
      navigate(`/workflows/advanced/${wf.id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="automations">
      <h1>{template.name[i18n.language as "ar" | "en"] ?? template.name.en}</h1>
      <label className="field">
        <span>{t("automations.title")}</span>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      {template.fields.map((field) => (
        <label className="field" key={field.key}>
          <span>{field.label[i18n.language as "ar" | "en"] ?? field.label.en}</span>
          <input
            value={values[field.key] ?? ""}
            onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
          />
        </label>
      ))}
      <button className="btn btn--primary" onClick={onSave} disabled={saving || !name}>
        {t("automations.save")}
      </button>
    </section>
  );
}
```

- [ ] **Step 5: Wire the routes**

In the router file found in Step 1, replace the existing `/workflows` route's element from `<WorkflowListPage />` to `<AutomationsPage />`, add `/workflows/templates/:templateId` → `<TemplateFormPage />`, and add `/workflows/advanced` → `<WorkflowListPage />` (the existing canvas entry keeps working, just at a new path) — following the exact JSX/route-object syntax already used by the surrounding routes in that file.

- [ ] **Step 6: Type-check**

Run: `cd apps/web && npx tsc -b`
Expected: no errors (fix any import-path mismatches surfaced here — they're expected on the first pass since Step 2/4's imports are written from the pattern in `ExecutionViewerPage.tsx`, not verified against this exact new file's neighbors)

- [ ] **Step 7: i18n parity check**

Run: `cd apps/web && node scripts/check-i18n-parity.mjs`
Expected: OK (no new keys introduced in this task beyond Task 8's)

- [ ] **Step 8: Commit**

```bash
git add apps/web/src/pages/workflows/ apps/web/src/[router file from Step 1]
git commit -m "feat(workflow): Automations page — template picker + template form"
```

---

### Task 11: Step-list builder — linear steps, no canvas

**Files:**
- Create: `apps/web/src/pages/workflows/StepListBuilderPage.tsx`
- Create: `apps/web/src/pages/workflows/StepListBuilderPage.css`
- Create: `apps/web/src/pages/workflows/steps/ApprovalStepForm.tsx`
- Create: `apps/web/src/pages/workflows/steps/ConditionStepForm.tsx`
- Create: `apps/web/src/pages/workflows/steps/NotificationStepForm.tsx`
- Test: `apps/web/src/lib/stepList.test.ts` (pure conversion logic — steps array ↔ nodes/edges graph)
- Create: `apps/web/src/lib/stepList.ts` (the pure conversion logic under test)

**Interfaces:**
- Consumes: `WorkflowGraph`'s `nodes`/`edges` shape (existing, from `api/types.ts`).
- Produces: `export interface Step { key: string; type: "approval" | "notification" | "condition" | "assistant_action" | "api_call"; config: Record<string, unknown>; branch?: { ifTrue: Step[]; otherwise: Step[] } }` (max one level of `branch` nesting — enforced by the type itself having no further nested `branch` inside `ifTrue`/`otherwise`'s own `Step` — wait: TypeScript can't express "no nesting" structurally in one type; enforce it in the UI instead, see Step 4); `stepsToGraph(steps: Step[]): { nodes: WorkflowNode[]; edges: WorkflowEdge[] }`; `graphToSteps(nodes: WorkflowNode[], edges: WorkflowEdge[]): Step[]` (best-effort — only used when re-opening a builder-created workflow; a hand-built canvas graph that isn't linear/one-branch falls back to "open in Advanced" instead of crashing, per Step 5).

- [ ] **Step 1: Write the failing test for the linear (no-branch) case**

```typescript
// apps/web/src/lib/stepList.test.ts
import { describe, expect, it } from "vitest";
import { stepsToGraph, graphToSteps, type Step } from "./stepList";

describe("stepsToGraph", () => {
  it("converts a linear step list into a start->step->end graph", () => {
    const steps: Step[] = [
      { key: "notify", type: "notification", config: { recipient: "ahmed" } },
    ];
    const { nodes, edges } = stepsToGraph(steps);
    expect(nodes.map((n) => n.key)).toEqual(["start", "notify", "end"]);
    expect(edges).toEqual([
      { source: "start", target: "notify", ordering: 0, condition: null },
      { source: "notify", target: "end", ordering: 0, condition: null },
    ]);
  });

  it("round-trips through graphToSteps", () => {
    const steps: Step[] = [
      { key: "notify", type: "notification", config: { recipient: "ahmed" } },
    ];
    const { nodes, edges } = stepsToGraph(steps);
    const roundTripped = graphToSteps(
      nodes.map((n) => ({ ...n, position: {} })),
      edges,
    );
    expect(roundTripped).toEqual(steps);
  });
});

describe("stepsToGraph with a branch", () => {
  it("converts one if/otherwise block into a condition node with two out-edges", () => {
    const steps: Step[] = [
      {
        key: "check_amount", type: "condition",
        config: { field: "amount_minor", operator: ">", value: 500000 },
        branch: {
          ifTrue: [{ key: "ask_approval", type: "approval", config: { approver_role: "finance_manager" } }],
          otherwise: [],
        },
      },
    ];
    const { nodes, edges } = stepsToGraph(steps);
    expect(nodes.map((n) => n.key)).toEqual(["start", "check_amount", "ask_approval", "end"]);
    const branchEdges = edges.filter((e) => e.source === "check_amount");
    expect(branchEdges).toHaveLength(2);
    expect(branchEdges.find((e) => e.target === "ask_approval")?.condition).toEqual({
      ">": [{ var: "amount_minor" }, 500000],
    });
    expect(branchEdges.find((e) => e.target === "end")?.condition).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npx vitest run src/lib/stepList.test.ts`
Expected: FAIL with `Cannot find module './stepList'`

- [ ] **Step 3: Write `stepList.ts`**

```typescript
// apps/web/src/lib/stepList.ts
/**
 * Converts between the step-list builder's linear/one-branch UI model and the same
 * nodes/edges graph shape the engine and the existing canvas already use (see
 * erp/workflow/services.py::save_graph). A step list is a *constrained view* over that graph —
 * it can only ever express start -> [steps] -> (one optional if/otherwise) -> ... -> end, so it
 * never emits a shape the engine can't already run.
 */
export interface Step {
  key: string;
  type: "approval" | "notification" | "condition" | "assistant_action" | "api_call";
  config: Record<string, unknown>;
  /** At most one branch per step list — enforced by the builder UI never nesting a second one. */
  branch?: { ifTrue: Step[]; otherwise: Step[] };
}

export interface GraphNode {
  key: string;
  type: string;
  config: Record<string, unknown>;
  position: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  ordering: number;
  condition: unknown | null;
}

function conditionFor(config: Record<string, unknown>): unknown {
  return { [config.operator as string]: [{ var: config.field }, config.value] };
}

export function stepsToGraph(steps: Step[]): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [{ key: "start", type: "start", config: {}, position: {} }];
  const edges: GraphEdge[] = [];
  let previousKey = "start";

  for (const step of steps) {
    nodes.push({ key: step.key, type: step.type, config: step.config, position: {} });
    edges.push({ source: previousKey, target: step.key, ordering: 0, condition: null });

    if (step.branch) {
      const [trueStep] = step.branch.ifTrue;
      if (trueStep) {
        nodes.push({ key: trueStep.key, type: trueStep.type, config: trueStep.config, position: {} });
        edges.push({ source: step.key, target: trueStep.key, ordering: 0, condition: conditionFor(step.config) });
        previousKey = trueStep.key;
      } else {
        previousKey = step.key;
      }
      // The "otherwise" path and the no-match fallback both land on whatever comes next (or end);
      // wired below via the end-fallback edge, matching the engine's single-fallback-edge rule.
      edges.push({ source: step.key, target: "end", ordering: 1, condition: null });
      nodes.push({ key: "end", type: "end", config: {}, position: {} });
      return { nodes: dedupe(nodes), edges };
    }
    previousKey = step.key;
  }

  nodes.push({ key: "end", type: "end", config: {}, position: {} });
  edges.push({ source: previousKey, target: "end", ordering: 0, condition: null });
  return { nodes: dedupe(nodes), edges };
}

function dedupe(nodes: GraphNode[]): GraphNode[] {
  const seen = new Set<string>();
  return nodes.filter((n) => (seen.has(n.key) ? false : (seen.add(n.key), true)));
}

export function graphToSteps(nodes: GraphNode[], edges: GraphEdge[]): Step[] {
  const byKey = new Map(nodes.map((n) => [n.key, n]));
  const outEdges = (key: string) => edges.filter((e) => e.source === key).sort((a, b) => a.ordering - b.ordering);

  const steps: Step[] = [];
  let current = outEdges("start")[0]?.target;
  while (current && current !== "end") {
    const node = byKey.get(current);
    if (!node) break;
    const out = outEdges(current);
    if (out.length === 2) {
      const trueEdge = out.find((e) => e.condition !== null);
      steps.push({
        key: node.key, type: node.type as Step["type"], config: node.config,
        branch: {
          ifTrue: trueEdge && trueEdge.target !== "end"
            ? [{ key: trueEdge.target, type: byKey.get(trueEdge.target)!.type as Step["type"],
                 config: byKey.get(trueEdge.target)!.config }]
            : [],
          otherwise: [],
        },
      });
      break; // one branch max — anything after it belongs to Advanced, not this builder
    }
    steps.push({ key: node.key, type: node.type as Step["type"], config: node.config });
    current = out[0]?.target;
  }
  return steps;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && npx vitest run src/lib/stepList.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Write `StepListBuilderPage.tsx`**

```tsx
// apps/web/src/pages/workflows/StepListBuilderPage.tsx
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useToast } from "../../app/ToastContext";
import { stepsToGraph, type Step } from "../../lib/stepList";
import { ApprovalStepForm } from "./steps/ApprovalStepForm";
import { ConditionStepForm } from "./steps/ConditionStepForm";
import { NotificationStepForm } from "./steps/NotificationStepForm";
import "./StepListBuilderPage.css";

// v1 scope: notification/approval/condition have real config forms (Step 7 below). assistant_action
// and api_call stay canvas/Advanced-only for now (spec Section 3's "script never exposed here" rule
// extended pragmatically — building their config forms means either reusing NodeConfigPanel's
// internals in a new context or duplicating them, and that's real, separately-planned work, not a
// two-line addition here). Add them to this list only once their step forms exist.
const STEP_TYPES = ["notification", "approval", "condition"] as const;

export function StepListBuilderPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const hasBranch = steps.some((s) => s.branch);

  function addStep(type: Step["type"]) {
    setSteps((s) => [...s, { key: `step_${s.length}`, type, config: {} }]);
  }

  function updateStep(index: number, config: Record<string, unknown>) {
    setSteps((s) => s.map((step, i) => (i === index ? { ...step, config } : step)));
  }

  async function onSave() {
    const { nodes, edges } = stepsToGraph(steps);
    const { createWorkflow } = await import("../../api/workflows"); // adjust to the real export name found in api/workflows.ts
    try {
      const wf = await createWorkflow({ name, nodes, edges });
      toast.show(t("automations.saved"), "success");
      navigate(`/workflows/advanced/${wf.id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  return (
    <section className="steplist">
      <h1>{t("automations.startFromScratch")}</h1>
      <label className="field">
        <span>{t("automations.title")}</span>
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>

      <ol className="steplist__steps">
        {steps.map((step, i) => (
          <li className="steplist__step" key={step.key}>
            <span className="steplist__label">
              {i === 0 ? t("automations.steps.do") : t("automations.steps.do")}
            </span>
            <strong>{t(`automations.steps.type.${step.type === "assistant_action" ? "assistant" : step.type === "api_call" ? "apiCall" : step.type}`)}</strong>
            {step.type === "approval" && <ApprovalStepForm config={step.config} onChange={(c) => updateStep(i, c)} />}
            {step.type === "notification" && <NotificationStepForm config={step.config} onChange={(c) => updateStep(i, c)} />}
            {step.type === "condition" && !hasBranch && (
              <ConditionStepForm config={step.config} onChange={(c) => updateStep(i, c)} />
            )}
          </li>
        ))}
      </ol>

      <div className="steplist__add">
        {STEP_TYPES.map((type) => (
          <button
            key={type}
            className="btn btn--sm"
            disabled={type === "condition" && hasBranch}
            onClick={() => addStep(type)}
          >
            + {t(`automations.steps.type.${type === "assistant_action" ? "assistant" : type === "api_call" ? "apiCall" : type}`)}
          </button>
        ))}
      </div>

      <button className="btn btn--primary" onClick={onSave} disabled={!name || steps.length === 0}>
        {t("automations.save")}
      </button>
    </section>
  );
}
```

Before finalizing this step, open `apps/web/src/api/workflows.ts` and replace the dynamic `import("../../api/workflows")` + `createWorkflow` call with whichever exact export that file already uses for `POST /api/workflows` (likely already named something like `saveWorkflow` or `createWorkflow` — match it exactly, and import it statically at the top of the file instead of dynamically, matching this codebase's convention seen in every other page file).

- [ ] **Step 6: Write `StepListBuilderPage.css`**

```css
.steplist__steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.steplist__step {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background-color: var(--color-surface-alt);
}

.steplist__label {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.steplist__add {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-block: var(--space-3);
}
```

- [ ] **Step 7: Write the three step config form components**

```tsx
// apps/web/src/pages/workflows/steps/ApprovalStepForm.tsx
import { useTranslation } from "react-i18next";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export function ApprovalStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <div className="steplist__form">
      <label className="field">
        <span>{t("automations.field.approverRole")}</span>
        <input
          value={(config.approver_role as string) ?? ""}
          onChange={(e) => onChange({ ...config, approver_role: e.target.value })}
        />
      </label>
    </div>
  );
}
```

```tsx
// apps/web/src/pages/workflows/steps/NotificationStepForm.tsx
import { useTranslation } from "react-i18next";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export function NotificationStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <div className="steplist__form">
      <label className="field">
        <span>{t("automations.field.recipient")}</span>
        <input
          value={(config.recipient as string) ?? ""}
          onChange={(e) => onChange({ ...config, recipient: e.target.value })}
        />
      </label>
    </div>
  );
}
```

```tsx
// apps/web/src/pages/workflows/steps/ConditionStepForm.tsx
import { useTranslation } from "react-i18next";

interface Props {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

const OPERATORS = [">", "<", "=="] as const;

export function ConditionStepForm({ config, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <div className="steplist__form">
      <label className="field">
        <span>{t("automations.field.amount")}</span>
        <input
          value={(config.field as string) ?? ""}
          onChange={(e) => onChange({ ...config, field: e.target.value })}
        />
      </label>
      <select
        value={(config.operator as string) ?? ">"}
        onChange={(e) => onChange({ ...config, operator: e.target.value })}
      >
        {OPERATORS.map((op) => (
          <option key={op} value={op}>{op}</option>
        ))}
      </select>
      <input
        value={(config.value as string) ?? ""}
        onChange={(e) => onChange({ ...config, value: Number(e.target.value) })}
      />
    </div>
  );
}
```

(This condition form uses a plain `<select>` for 3 static operators — acceptable per the project's `field-primitives-standard` rule, which reserves `ComboBox` for long/dynamic option lists.)

- [ ] **Step 8: Type-check**

Run: `cd apps/web && npx tsc -b`
Expected: no errors after correcting the `createWorkflow` import per Step 5's note

- [ ] **Step 9: i18n parity check**

Run: `cd apps/web && node scripts/check-i18n-parity.mjs`
Expected: OK

- [ ] **Step 10: Wire the `/workflows/build` route**

In the router file (found in Task 10 Step 1), add `/workflows/build` → `<StepListBuilderPage />`.

- [ ] **Step 11: Commit**

```bash
git add apps/web/src/lib/stepList.ts apps/web/src/lib/stepList.test.ts apps/web/src/pages/workflows/
git commit -m "feat(workflow): step-list builder — linear steps + one-branch condition, no canvas"
```

---

### Task 12: Demote the existing canvas to /workflows/advanced

**Files:**
- Modify: `apps/web/src/pages/WorkflowNav.tsx`
- Modify: the router file (already touched in Tasks 10/11)

**Interfaces:**
- Consumes: existing `WorkflowNav.tsx` tab structure (open it first — it currently renders "Workflows"/"Runs" tabs per the 2026-07-20 P1 fix; read its exact JSX before editing).

- [x] **Step 1: Read the current nav**

Open `apps/web/src/pages/WorkflowNav.tsx` in full.

- [x] **Step 2: Add an "Advanced" tab**

Following the exact pattern of the existing "Workflows"/"Runs" `<NavLink>` (or equivalent) entries in that file, add a third tab linking to `/workflows/advanced`, labelled via `t("automations.advanced")` (already added in Task 8).

- [x] **Step 3: Confirm `/workflows` now defaults to Automations, not the canvas**

Run: `cd apps/web && npx tsc -b` (confirms no dangling references to the old default route)

Manually verify in the running dev server: navigate to `/workflows`, confirm `AutomationsPage` renders (not the canvas list); navigate to `/workflows/advanced`, confirm the existing `WorkflowListPage`/canvas still works unchanged.

- [x] **Step 4: Commit** — `a42919d` 2026-07-23

```bash
git add apps/web/src/pages/WorkflowNav.tsx
git commit -m "feat(workflow): demote graph canvas to /workflows/advanced"
```

---

### Task 13: Arabic-only end-to-end walkthrough (spec Section 6 acceptance)

**Files:** none created — this is a verification task using the running app.

- [x] **Step 1: Start the dev servers**

Use the `preview_start` tool (or `run-dev.ps1` per `erp-status`) to start both Django (`:8000`) and Vite (`:5173`/`:5174`).

- [x] **Step 2: Set the UI language to Arabic**

Log in, go to Settings → Profile, set language to `ar` (per `erp-status`'s documented language-switch location — the 4th `.setrow`).

- [x] **Step 3: Drive the whole builder in Arabic, screenshot/read_page at each stop**

Walk: `/workflows` (confirm template names render in Arabic, not template ids) → click "Ask for approval above an amount" template card (confirm it reads `طلب موافقة عند تجاوز مبلغ`, not `approval_above_amount`) → fill the form (confirm field labels are `المبلغ`/`من يوافق`, not `amount`/`approver_role`) → save → confirm the toast reads `تم حفظ الأتمتة` → navigate to `/workflows/build` → add each step type via the "+" buttons (confirm every button label is Arabic, not `notification`/`approval`/`condition`) → open the condition step form (confirm no raw JSON, no English leaking).

- [x] **Step 4: Confirm zero Latin-script identifier leakage**

Use `read_page` (`filter: "all"`) at each stop from Step 3 and grep the returned text for any of: `approval_above_amount`, `low_stock_alert`, `overdue_invoice_reminder`, `new_lead_followup`, `ticket_escalation`, `amount_minor`, `approver_role`, `api_call`, `assistant_action`. None should appear anywhere in the rendered Arabic UI.

- [x] **Step 5: Record the result**

**PASSED 2026-07-23.** All five template names render in Arabic. Form labels Arabic (الأتمتة / المبلغ / من يوافق). Toast reads `تم حفظ الأتمتة`. StepListBuilder add-step buttons all Arabic (أرسل إشعارًا / اطلب موافقة أحدهم / تحقق من شرط). Notification + condition step forms: no leaks. Zero raw-identifier leaks across all screens.
**Bug found + fixed during this task:** workflow migrations 0005–0007 (notification NodeType + WorkflowTrigger model + schedule field) were not applied to the dev DB → save returned 500. Fixed with `manage.py migrate workflow` (and `migrate` for 2 other pending: inventory + sales).

---

### Task 14: End-to-end acceptance test — one template, full path

**Files:**
- Modify: `apps/web/e2e/specs/workflow.spec.ts` (add to the existing file — do not create a new spec file, matching this repo's one-spec-per-feature-area convention)

**Interfaces:**
- Consumes: the existing Playwright test setup in `workflow.spec.ts` (open it first for its login/setup helpers before writing the new test).

- [ ] **Step 1: Read the existing spec's setup helpers**

Open `apps/web/e2e/specs/workflow.spec.ts` in full — note its login helper, base URL, and existing test structure.

- [ ] **Step 2: Write the new test**

Add a test following the exact style of the existing tests in that file:

```typescript
test("approval-above-amount template creates a working automation", async ({ page }) => {
  // reuse this file's existing login helper here instead of re-authenticating manually
  await page.goto("/workflows");
  await page.getByText("Ask for approval above an amount").click();
  await page.getByLabel("Automations").fill("E2E approval template test");
  await page.getByLabel("Amount").fill("500000");
  await page.getByLabel("Who approves").fill("finance_manager");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Automation saved")).toBeVisible();
});
```

Adjust the `getByLabel`/`getByText` selectors to match the actual rendered `aria-label`s/text once Tasks 10-11 exist — this plan cannot know the exact accessible names until those components are built; the implementer verifies each selector against the real DOM (via `read_page` or Playwright's own trace) before considering this step done, not by assuming the strings above are pixel-perfect.

- [ ] **Step 3: Run the E2E test**

Run: `cd apps/web && npx playwright test workflow.spec.ts -g "approval-above-amount"`
Expected: PASS

- [ ] **Step 4: Run the full E2E workflow spec to check for regressions**

Run: `cd apps/web && npx playwright test workflow.spec.ts`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add apps/web/e2e/specs/workflow.spec.ts
git commit -m "test(workflow): E2E acceptance for the approval-above-amount template"
```

---

## Final acceptance (run once, after all 14 tasks)

- [ ] Backend: `.venv/Scripts/python.exe -m pytest erp/workflow erp/sales erp/crm erp/inventory erp/notifications -q` — all pass
- [ ] `.venv/Scripts/python.exe scripts/gates/_run.py all` (00-17) — green
- [ ] Frontend: `cd apps/web && npx tsc -b && node scripts/check-i18n-parity.mjs && npm run test` — all green
- [ ] `python scripts/gates/gate03.py` (repo root) — exit 0
- [x] Task 13's Arabic-only walkthrough — zero raw-identifier leaks found (PASSED 2026-07-23)
- [ ] Update the `erp-e-invoice`-style status skill (or `erp-status` directly) with: this feature's completion, the new `/workflows` default landing page, and the fact the graph canvas moved to `/workflows/advanced`
