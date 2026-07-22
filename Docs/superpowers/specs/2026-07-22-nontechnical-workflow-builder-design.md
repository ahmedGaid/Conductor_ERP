# Non-technical workflow builder — design

**Date:** 2026-07-22
**Status:** approved by founder, ready for implementation planning

## Problem

The workflow feature (`Docs/plan/ai-workspace-plan/` + `erp/workflow/`) is developer-shaped end to
end: authoring is a React Flow graph canvas with raw JSON config boxes, node types are dev words
(`api_call`, `script`, `condition`), and (until the 2026-07-22 log-honesty fix) run history narrated
in raw English/JSON. Per the ARP positioning, workflows must be built and read by the SMB owner or
their staff directly — no developer or reseller in the loop. In its current shape, a non-technical
user can neither build a workflow nor understand one that ran. This spec covers making both
possible without inventing a general-purpose no-code platform — ERP automations have a narrow,
known shape (see below), and the design should fit that shape exactly rather than over-build.

Out of scope: rebuilding the execution engine, the DB schema, or the existing graph canvas (kept,
demoted). This is an authoring-layer + trigger-layer addition on top of what already runs.

## Context found during brainstorming

- No real customer workflows exist yet (pre-launch) — the only DB rows are 32 synthetic E2E test
  fixtures, all `start → script → end`, zero branching. Real complexity ceiling is inferred from
  ARP's actual use cases (approval thresholds, low-stock alerts, overdue reminders), not from data.
- Workflows today start only two ways: a form-submission trigger (`forms/services.py`), or a manual
  "Run" button (`workflow/views.py`). No "when X happens in the ERP, start this automatically"
  mechanism exists.
- A 34-event catalog (`notifications/webhook_catalog.py`, `WEBHOOK_EVENT_CATALOG`) already backs
  Webhooks — every domain event any module publishes on `erp.core.events.bus`
  (`PR_SUBMITTED`, `STOCK_ISSUED`, `ORDER_INVOICED`, etc.). Webhooks already subscribe to this same
  catalog; a workflow trigger is structurally the same subscription, just starting an instance
  instead of firing an HTTP call.
- CRM already runs a periodic "sweep" job (ticket escalation, `runEscalations` / the engine that
  powers it) — the same shape needed for triggers that aren't a single discrete event (low-stock
  check, overdue-invoice check run daily over the affected records).
- The 2026-07-22 session (`e20dd20`) already fixed run-log narration (translated event codes,
  labelled input/output rows instead of raw JSON) — this spec's Arabic-parity requirement extends
  that same discipline to the new authoring surface.

## Approach: templates + step-list builder, canvas demoted

Two other approaches were considered and rejected:
- **Keep the graph canvas, just relabel it** — rejected: the canvas metaphor itself (nodes, edges,
  drag-connect) is unfamiliar to a non-technical user regardless of labelling; the real complexity
  ceiling (mostly linear, one branch point) doesn't need a graph at all.
- **Fixed templates only, no customization** — rejected: covers the common cases fast but leaves no
  path for a shop owner whose approval chain has one extra step; a pure template list becomes a
  dead end the moment reality doesn't match one of the five.

The chosen shape: **templates are the front door, a step-list editor is the escape hatch, the
existing graph canvas is kept but demoted to an advanced/support-only surface.**

## 1. Trigger mechanism

New `WorkflowTrigger` model: `workflow` (FK), `event_name` (validated against
`WEBHOOK_EVENT_CATALOG`, reusing the exact same catalog and bus subscription pattern Webhooks use),
an optional simple condition (`field`, `operator`, `value` — e.g. `amount_minor > 500000`).
Dispatches off the same event bus Webhooks already listen on; this is a second subscriber type, not
new plumbing.

For triggers that aren't a single event — "stock below reorder point," "invoice overdue by N
days" — a scheduled sweep, same shape as the existing ticket-escalation sweep, runs daily and starts
workflow instances for each matching record. This needs one new sweep-runner per scheduled-trigger
type (low-stock, overdue-invoice), following the ticket-escalation sweep's existing pattern in
`erp/crm` (find the equivalent module/job and mirror its structure — do not build a generic
"scheduled trigger" abstraction beyond what these ~2 concrete sweeps need; YAGNI).

The template/step-list UI never shows event names or the catalog directly — always the plain-Arabic
(or plain-English in `en`) phrasing mapped from it (see Section 6).

## 2. Template catalog (v1 — five fixed recipes)

1. **Approval above an amount** — "When a [purchase request / sales order] is submitted, if its
   total is above [amount], ask [role/person] to approve." Trigger: `PR_SUBMITTED` or the
   equivalent order-submit event → condition on amount → approval step.
2. **Low stock alert** — "Every day, check items below their reorder point and notify [person]."
   Scheduled sweep over `Item.reorder_point` (existing field).
3. **Overdue invoice reminder** — "When an invoice is [N] days overdue, remind
   [customer/salesperson]." Scheduled sweep over unpaid invoices.
4. **New lead follow-up** — "When a new lead comes in, remind [salesperson] to follow up within
   [N] days." Event-based (lead-created event) or a short sweep, whichever the actual CRM lead
   model supports more directly — confirm against `erp/crm/models.py` at implementation time.
5. **Ticket escalation** — already exists as CRM-only hardcoded logic (`runEscalations`); fold it
   into this same template system so it becomes an editable/toggleable template like the other
   four, instead of special-cased code the owner can't see or adjust.

Each template = pick a workflow name, fill 2–4 plain fields (amount, person, days), save. No
step-list editing required unless the owner customizes further.

## 3. Step-list builder (the escape hatch)

- Steps render as a vertical list: `When [trigger]` at the top, then `Do [step]`, `Do [step]`, ...,
  with an inline `If [condition] → do [step], otherwise → do [step]` block wherever a branch is
  needed. **Max one level of branch nesting** — matches the real complexity ceiling; anything
  needing more belongs on the advanced canvas, not this builder.
- Step types map 1:1 onto the existing `NodeType`s, relabeled in plain language: "Send a
  notification," "Ask someone to approve," "Let the assistant draft something," "Check a
  condition," "Call another system" (`api_call`, rarely user-facing). **The `script` node type is
  never exposed here** — scripting stays canvas/advanced-only.
- Under the hood, the step-list is a linear/one-branch-max subset of the same
  `Workflow`/`WorkflowNode`/`WorkflowEdge` schema — no new engine, no new node types, no new DB
  tables for the graph itself (`WorkflowTrigger` from Section 1 is the only new table). The builder
  is a constrained view over the existing schema: it can only emit shapes the engine already runs.
- Adding/reordering steps = list operations (insert a card, drag to reorder within the line), not
  graph editing (no canvas, no manual edge-drawing).

## 4. Config forms (replace JSON boxes)

- **Approval step:** a form — "Ask [ComboBox: role/person]," optional message field. No JSON.
- **Assistant-action step:** keep the existing action picker (already exists, per
  `canvas.assistant.action*` i18n keys) — just relabel for this surface, no new picker needed.
- **Condition step:** a structured comparator — `[field] [operator: </>/=] [value]` — replacing the
  raw JSON condition blob. Field choices come from the trigger's event payload shape (e.g. `amount`,
  `days_overdue`), offered as a ComboBox, never free-typed.
- **Notification/api_call steps:** structured fields (recipient, message template). Message
  templates still use the existing `{{ ctx.path }}` token syntax (`workflow/lib/template.py`,
  unchanged), but the path itself is chosen from a ComboBox of available fields, not hand-typed.

## 5. Compatibility / rollout

- Execution engine (`engine.py`), `NodeType`, DB schema for `Workflow`/`WorkflowNode`/
  `WorkflowEdge`/`WorkflowInstance`: **unchanged.** This is purely an authoring-layer
  (templates + step-list UI) and trigger-layer (`WorkflowTrigger` + sweeps) addition.
- The existing graph canvas (`WorkflowCanvasPage.tsx`) stays in the codebase, demoted to an
  "Advanced" entry point — reachable, not the default landing page for Workflows.
- The 32 existing workflow rows are E2E test fixtures, not real customer data — no migration
  concern, no backfill needed.

## 6. Arabic-first, no leaked identifiers (hard requirement)

- Every dynamic label the builder shows — trigger names, event-payload field names, step-type
  names, condition operators, the generated "recipe sentence" preview — must resolve through an
  i18n lexicon entry. **Never render a raw event name (`PR_SUBMITTED`), model field
  (`amount_minor`), or `NodeType` value (`api_call`) directly to the user**, in either language.
- One canonical Arabic term per concept (Identity System §6 — e.g. the same word Purchasing already
  uses for "purchase request" everywhere, not a fresh term invented for this feature).
- `WEBHOOK_EVENT_CATALOG` needs an Arabic (and English) display-name map added for use here. The
  existing Webhooks settings page can keep showing raw event names to admins (that's an accepted
  power-user surface per the brand-review P1 fix already shipped) — but the template/step-list
  builder is for a non-technical owner and must never show that raw form.
- Same rule for event-payload field names surfaced in the condition-builder ComboBox — each needs a
  human Arabic label, not the raw key.
- Generated sentence previews ("When a purchase request is submitted, if its total is above 5,000,
  ask Ahmed to approve") must read as natural Arabic grammar in `ar` — checked per string against
  real Arabic sentence structure, not assumed correct because the English template translated
  word-for-word. Numbers interpolated into these sentences must use the same CLDR-plural discipline
  as the 2026-07-22 plural-agreement fix (`ed1d9f4`) where the sentence contains a count.
- **Acceptance for this section specifically:** drive the entire builder end to end with the UI set
  to `ar` and the OS/browser in Arabic, confirm zero Latin-script/raw-identifier leakage anywhere in
  the flow — this is a checklist item in acceptance testing, not assumed from translation-file
  coverage alone.

## Testing / acceptance (high level — detail belongs in the implementation plan)

- Backend: `WorkflowTrigger` model + event-bus subscription tested like the existing Webhook
  dispatch tests; scheduled sweeps tested like the existing ticket-escalation sweep tests.
- Frontend: each of the 5 templates produces a working, runnable workflow end to end (template →
  save → trigger fires → instance runs → log is readable) — mirrors the existing E2E workflow spec
  (`apps/web/e2e/specs/workflow.spec.ts`) pattern.
- i18n parity gate (`check-i18n-parity.mjs`) plus the Section 6 live Arabic-only walkthrough.
- `pytest erp/workflow erp/notifications`, `tsc -b`, `gate03.py` all green before merge.

## Open questions for the implementation plan (not blocking this design)

- Exact CRM lead-created event/field names for template 4 (confirm against `erp/crm/models.py` and
  `erp/crm/events.py` at plan time — not looked up in this brainstorming session).
- Whether the low-stock and overdue-invoice sweeps run as one shared periodic-sweep job with
  per-template logic, or two separate jobs — an implementation-plan decision, not a design one;
  either is compatible with this spec.
