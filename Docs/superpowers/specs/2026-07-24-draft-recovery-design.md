# Persistent WIP / Draft Recovery — design

**Date:** 2026-07-24
**Status:** approved (brainstorm), ready for implementation planning
**Scope:** a reusable platform capability that preserves unfinished work across the ERP so a user
can leave and return to *exactly* where they were — plus the new edit-record forms that give the
capability somewhere to attach on the "edit an existing record" path.

---

## 1. Problem

Whenever a user starts data entry and does not finish (intentional close, tab close, browser/app
crash, navigation away, network drop, long idle), their in-progress work must be preserved and
offered back on return. This must hold for creation flows, multi-step wizards, and long-running
imports. The user should never silently lose meaningful entered work, and recovery must feel calm
(no intrusive "are you sure you want to leave?" dialogs) — a subtle "Saved" status, and a clear
"Continue where you left off?" surface on return.

Hard separation the design must preserve: a **draft** (unsaved form state) is *not* a **partially
executed business transaction**. Financial postings stay atomic; we never create partial business
records to implement recovery.

## 2. What already exists (do not duplicate)

Verified via CodeGraph against the current tree:

- **Smart Import already persists durable state server-side.** `ImportBatch` (status machine:
  `analyzing → mapping → previewing → ready → running → paused → done → failed → rolled_back`) and
  `ImportRow` (per-row raw/normalized/issues/decision/result_ref) live in `erp/imports/models.py`.
  The runner supports pause/resume/cancel/rollback (`erp/imports/api/views.py` `PauseView`,
  `ResumeView`, `CancelView`, `RollbackView`), and `ImportWizard.tsx` already **resumes by URL/batch
  id** — reload or open `/imports/{id}` routes to the right step by batch status. → For imports we
  add only a thin *pointer*, never a second persistence system.
- **No generic draft/autosave anywhere.** Create forms (`NewCustomer`/`NewOrderPage`/
  `NewPurchaseOrderPage`, etc.) hold scattered `useState`; nothing survives a reload.
- **Editing existing records barely exists:**
  - Customer: **no edit endpoint** — `CustomerDetailPage` is read-only (`PartyDetailView`).
  - Item: `ItemDetailView.patch` restricts to ETA-coding fields only ("the only editable fields on
    an existing item").
  - Sales order: `update_order_lines` service **exists** (`erp/sales/services/orders.py:173`,
    draft-only) but has no edit UI.
  - Purchase order: neither an update-lines service nor an edit UI.
- **Service-contract + RBAC patterns are consistent and reusable:** module contracts
  (`erp.sales.contracts.create_customer`, `erp.inventory.contracts.create_item`), DRF permission
  classes (`HasAnyRole.require(...)`, `HasModulePermission.require(...)` — superuser / System Admin
  bypass), and owner-scoped record access (`imports` `_get_owned_batch`). `TimeStampedModel` gives
  uuid pk + `created_at`/`updated_at`; `AuditedModel` adds actor/branch/soft-delete.
- **Frontend building blocks:** `apiFetch` envelope + cache invalidation (`api/client.ts`),
  `useFormKeys` (⌘/Ctrl+Enter, Esc), toast/optimistic primitives, `ComboBox`/`DatePicker`,
  design tokens + logical CSS + ar/en parity gate.

## 3. Shape — two projects, one foundation

Delivered as **one spec** but sequenced so Project 1 never blocks on Project 2.

- **Project 1 — WorkSession foundation.** The reusable capability (backend module + service + API,
  frontend hook + recovery UI), wired into the five originally-listed workflows: create customer,
  create item, create sales order, create purchase order, Smart Import.
- **Project 2 — Edit-record forms.** New multi-field edit UI *and* the new backend PATCH contracts
  it requires for Customer / Item / Sales Order / Purchase Order, each then wired to the same
  recovery hook. Larger, and gated behind per-entity "which fields are editable after creation"
  domain calls and brand review of the new screens.

## 4. Foundation architecture — backend

New Django module **`erp/worksessions/`** (module-agnostic, mirroring how `erp/imports/` is its own
module). Mounted at `/api/worksessions` and included in `config/urls.py`.

### 4.1 `WorkSession` model (`erp/worksessions/domain/models.py`)

Extends `TimeStampedModel` (uuid pk + `created_at`/`updated_at`).

| Field | Type | Purpose |
|---|---|---|
| `owner` | FK → user (`PROTECT`/`CASCADE` per convention) | Draft is private to its owner. |
| `workflow_key` | CharField(64) | Namespaced form identity, e.g. `sales.customer.create`, `purchasing.order.create`, `sales.customer.edit`. |
| `entity_type` | CharField(64), blank | Display/grouping label. |
| `related_entity_id` | CharField(64), blank | Empty for a create draft; the record's code/id for an edit draft (or set after creation). |
| `status` | TextChoices: `active`, `completed`, `discarded`, `superseded` | **Draft** lifecycle only — never the business record's lifecycle. |
| `payload` | JSONField(default=dict) | The form draft: field values + current step + any wizard sub-state. |
| `schema_version` | PositiveIntegerField(default=1) | Form payload shape version; a stale-shape draft is discarded/ignored rather than mis-applied. |
| `client_version` | PositiveIntegerField(default=0) | Monotonic counter; drives last-write-wins + conflict detection. |
| `last_active_at` | DateTimeField | Touched every save; drives "10 minutes ago" + TTL cleanup. |
| `import_batch` | FK → `"imports.ImportBatch"`, null, `SET_NULL` | Links a Smart-Import work session to its durable job. Declared with a **string app-label** (`"imports.ImportBatch"`) so Django resolves it lazily — no Python-level cross-module import, matching how `imports` itself references `"assistant.Attachment"`. Keeps `worksessions` module-agnostic. |

Meta:
- index on `(owner, workflow_key, status)` and `(owner, status, last_active_at)`.
- **partial unique constraint**: at most one `status="active"` row per
  `(owner, workflow_key, related_entity_id)` → structurally prevents duplicate drafts for the same
  form. (Postgres partial unique index via `condition=Q(status="active")`.)

Status semantics: `active` = a live draft; `completed` = the real entity was saved (archive, stop
offering); `discarded` = user threw it away; `superseded` = replaced (e.g. schema bump, or a newer
device won a conflict).

### 4.2 Service layer (`erp/worksessions/services.py`)

Pure draft bookkeeping — **never touches a business model.** All functions owner-scope.

- `upsert_draft(owner, *, workflow_key, payload, entity_type="", related_entity_id="",
  schema_version, client_version, expected_version=None) -> UpsertResult`
  Creates or updates the single active session for the key. If `expected_version` is provided and is
  **less than** the stored `client_version`, the stored draft was updated elsewhere since this
  client last read it → return `UpsertResult(session, conflict=True)` **without** clobbering (the
  API turns this into the warn-banner signal). Otherwise write, bump stored `client_version`, touch
  `last_active_at`, return `conflict=False`. Never raises on a normal conflict — last-write-wins is
  a *client* decision after the warn.
- `get_active(owner, workflow_key, related_entity_id="") -> WorkSession | None`
- `list_active(owner) -> list[WorkSession]` — for the drafts surface / multiple-drafts list.
- `complete(owner, session_id, *, related_entity_id="") -> None` — flip to `completed`, stamp
  `related_entity_id` if now known. Called after the real create/update contract succeeds.
- `discard(owner, session_id) -> None` — flip to `discarded`.
- `supersede_stale(owner, workflow_key, ...)` — internal helper for schema-version mismatch.

Cleanup: a management command / periodic task (Celery beat already exists) hard-deletes
`discarded`/`completed` older than N days and `active` idle past a TTL (e.g. 30 days) — keeps the
table bounded. Not required for MVP correctness; include as a follow-up task in the plan.

### 4.3 API (`erp/worksessions/api/`)

`permission_classes = [IsAuthenticated]`; every view owner-scopes through a `_get_owned_session`
helper (mirrors `imports._get_owned_batch`) → a user can never read/mutate another user's draft.
Response uses the standard `{data}` envelope.

- `GET /worksessions` → `list_active` for the current user (drafts surface).
- `GET /worksessions/active?workflow_key=&related_entity_id=` → the one active draft, or `null`.
- `POST /worksessions` → `upsert_draft`; body `{workflow_key, payload, entity_type,
  related_entity_id, schema_version, client_version, expected_version}`. Response includes
  `{session, conflict}`. The unload flush hits this same endpoint via `fetch(keepalive:true)` (see
  5.1) — a normal authenticated JSON POST, no special server handling needed.
- `POST /worksessions/{id}/discard`
- `POST /worksessions/{id}/complete` → body `{related_entity_id?}`.

### 4.4 Tests (`erp/worksessions/tests/`)

- Service: upsert create/update, `get_active`, `list_active`, `complete`/`discard` transitions;
  **owner-scoping denies cross-user access**; conflict path (`expected_version` < stored) returns
  `conflict=True` and does not clobber; unique-active constraint blocks a second active row.
- API: auth required; owner-scoping (user B 404/403 on user A's session); beacon body parses;
  envelope shape.

## 5. Foundation architecture — frontend (`apps/web/src`)

### 5.1 `hooks/useDraftRecovery.ts` — the one primitive

Signature (shape, not final):
```
useDraftRecovery<T>({
  workflowKey: string,
  value: T,                       // current form state (single object)
  schemaVersion: number,
  relatedEntityId?: string,
  enabled?: boolean,              // default true
  isMeaningful?: (v: T) => boolean, // default: value differs from the empty/initial baseline
}) => {
  status: "idle" | "saving" | "saved",
  savedAt: Date | null,
  recoverable: { payload: T; lastActiveAt: string } | null,
  recover: () => T,               // page applies the returned payload to its state
  discard: () => Promise<void>,
  complete: (relatedEntityId?: string) => Promise<void>,
  conflict: boolean,              // drives the warn banner
}
```

Behaviour:
- **On mount:** `GET /worksessions/active`. If an active draft exists and is meaningful, do **not**
  auto-apply — expose it as `recoverable` so the page renders the recovery banner. Reconcile against
  the localStorage mirror (below): if the local copy is newer (server save was mid-flight at crash),
  prefer the local copy for `recoverable`.
- **While editing:** debounced autosave — **idle 800 ms, 5 s max-wait** (a long typing burst still
  flushes within 5 s), meaningful-change only (diff against last-saved payload). Each save posts
  `upsert_draft` with the client's `client_version+1` and `expected_version = lastKnownServerVersion`.
- **Local safety layer:** on every meaningful change, mirror the payload to `localStorage` under a
  namespaced key (`erp.draft.<workflowKey>.<relatedEntityId>`). This is the offline/mid-flight
  backstop — reconciled on mount, cleared on complete/discard. The feature does **not** depend on
  localStorage as the source of truth (server is authoritative).
- **On unload/hide:** `visibilitychange`→hidden and `pagehide` flush the latest pending payload via
  `fetch("POST /worksessions", { keepalive: true })`. `keepalive` lets the request outlive the page
  (tab-close/crash) **and** carry the in-memory JWT `Authorization` header — which `sendBeacon`
  cannot set, so a beacon would post unauthenticated (401). Body is well under keepalive's 64 KB
  limit. No `beforeunload` prompt.
- **Cross-tab / multi-device conflict:** a `storage` event listener notices a sibling tab's write;
  the server `client_version` returned on each save detects a stale write → set `conflict=true`,
  which the page surfaces as a warn banner ("This draft changed elsewhere — keep editing / reload").
- **On complete:** call `complete()` after the page's real create/update contract succeeds; clears
  local mirror and stops offering the draft.

### 5.2 Pure logic extracted to `lib/draftRecovery.ts` (Vitest-tested)

Per CLAUDE.md (pure-logic modules get a unit test), pull the framework-free decisions here:
- debounce/max-wait scheduler decision (given last-save time + now → save now?),
- meaningful-change diff,
- mount reconcile (server payload+version vs local payload+version → which to offer),
- conflict decision (expected vs stored version).
Unit-test each; the hook is a thin React shell over these.

### 5.3 Recovery UI (all strings ar/en, tokens + logical CSS, brand-checked)

- `components/DraftRecoveryBanner.tsx` — calm "Continue where you left off?" with the entity/context
  line, relative "last saved N minutes ago", **Continue** and **Discard**. Follows the existing
  `sysbanner`/status-note visual language; no colour in chrome.
- `components/DraftStatusIndicator.tsx` — subtle inline "Saving… / Saved / Changes saved" driven by
  `status`/`savedAt`. Non-intrusive.
- Drafts surface (`pages/drafts/` or a section in an existing "recent" area) — lists `list_active`
  drafts: entity/workflow name, last-updated, current step/progress, Continue / Discard. Satisfies
  "if multiple drafts exist, show a list." Designed empty state.
- `api/workSessions.ts` — typed wrappers (`getActiveDraft`, `listDrafts`, `saveDraft`,
  `discardDraft`, `completeDraft`) over `apiFetch`, plus a `flushDraft` unload variant using
  `fetch(keepalive:true)` with the bearer header.

### 5.4 Wiring the five creation flows

Per page: consolidate scattered `useState` into one draft object; call `useDraftRecovery`; render
`<DraftRecoveryBanner>` when `recoverable`; render `<DraftStatusIndicator>`; call `complete()` after
the existing create contract returns. No change to the business write path.

- `sales.customer.create`, `inventory.item.create` — simple single-object forms (prove the pattern).
- `sales.order.create`, `purchasing.order.create` — line-array forms (payload includes the lines).
- **Smart Import** — special: the durable job is `ImportBatch`. The WorkSession is thin — created at
  upload with `import_batch` set and payload holding only the wizard step pointer; the batch stays
  the source of truth for rows/validation/progress. Recovery = "you have an import in progress" in
  the drafts surface → routes into the existing `ImportWizard` resume-by-id path. No import
  persistence is rebuilt.

## 6. Project 2 — edit-record forms

Each entity needs a backend edit path *and* a new edit form, then the same hook with
`workflowKey: "<entity>.edit"` and `relatedEntityId: <code/id>`.

- **Customer** (`sales.customer.edit`): new `update_customer` service contract + PATCH view +
  serializer covering name / phone / tax id / national id / credit limit / custom fields; new edit
  form UI. (Detail page is read-only today.)
- **Item** (`inventory.item.edit`): broaden beyond ETA fields to name / uom / reorder_point via a
  service contract + widened PATCH view; new edit form. **Domain call:** which fields are immutable
  once stock movements exist (e.g. `type`, possibly `sku`) — decide per field in the plan.
- **Sales order** (`sales.order.edit`): `update_order_lines` **exists** (draft-only) — add the PATCH
  view if missing + a draft-order edit form; gate strictly to `status="draft"`.
- **Purchase order** (`purchasing.order.edit`): add an `update_order_lines` equivalent service +
  view + draft-order edit form, gated to draft.

Conflict on the edit path has an extra dimension: the **live record changed on the server** since
the draft began. Draft-vs-draft is covered by `client_version`; record-vs-draft compares the
record's own `updated_at` captured when the draft started against the current value at save time,
surfacing the same warn banner. Every write still goes through the module service contract; RBAC and
service-layer validation are unchanged; no raw ORM `.create()`/`.update()` for business mutations.

New screens ⇒ Conductor Quality Review + brand-feel checklist per entity.

## 7. Cross-cutting requirements → where satisfied

- **Survives close/tab-close/crash/restart/nav/offline/idle** → server-authoritative drafts (4.1)
  + localStorage mirror + `fetch(keepalive)` flush on hide/unload (5.1).
- **Detect existing draft, never silently overwrite, clear recovery UI, Continue/New/Discard** →
  mount fetch + `DraftRecoveryBanner` (5.1, 5.3).
- **Multiple drafts distinguishable** → drafts surface (5.3), `list_active` (4.2).
- **No `beforeunload` nag** → hide/`pagehide` beacon instead (5.1).
- **Completed workflow doesn't reappear** → `complete()` flips status (4.2, 5.1, 5.4).
- **User can discard** → `discard()` (4.2, 5.3).
- **RBAC blocks other users' private drafts** → `IsAuthenticated` + owner-scoped views (4.3).
- **Business transactions stay atomic; no duplicate/partial records** → WorkSession service never
  writes business models; real writes stay in existing atomic contracts (4.2, 5.4, 6).
- **ar/en parity, tokens, logical CSS, no new deps, reuse primitives** → 5.3, and the frontend gate.
- **Long-running import recoverable after interruption** → reuse `ImportBatch` + existing
  resume/pause/rollback; WorkSession is only a pointer (5.4).
- **Smart Import distinguishes draft vs in-progress vs importing vs done/failed/cancelled/
  recoverable** → already modelled on `ImportBatch.Status`; the WorkSession does not re-model it.

## 8. Testing & gates

- Backend: `erp/worksessions/tests/` (service + API, §4.4). Existing gates unaffected; add a small
  gate assertion only if the roadmap wants one.
- Frontend: `lib/draftRecovery.test.ts` (Vitest, §5.2). Manual browser verification of each wired
  flow (autosave indicator, leave+return recovery, reload recovery, discard, conflict banner,
  Smart-Import resume).
- Before "done" (from `apps/web`): `node scripts/check-i18n-parity.mjs`, `npx tsc --noEmit`,
  `npm run test`; repo root `python scripts/gates/gate03.py`; `conductor-brand` checklist for new
  surfaces.

## 9. Rollout checkpoints (→ implementation plan; each a natural session split)

**Project 1**
- **1A** — `worksessions` module: model + migration + service + API + tests.
- **1B** — frontend: `useDraftRecovery` + `lib/draftRecovery.ts` + `api/workSessions.ts` +
  `DraftRecoveryBanner` + `DraftStatusIndicator` + drafts surface + i18n.
- **1C** — wire create-customer + create-item (prove the pattern on the two simplest).
- **1D** — wire create sales order + create purchase order (line-array payloads).
- **1E** — Smart Import pointer + drafts-surface entry (reuse existing resume path).

**Project 2**
- **2A** — customer edit (contract + view + serializer + form + recovery).
- **2B** — item edit (widen editable fields + form + recovery).
- **2C** — sales order edit (draft; service exists) + recovery.
- **2D** — purchase order edit (new update-lines service + view + form + recovery).

## 10. Explicit non-goals (YAGNI)

- No real-time collaborative editing / operational-transform merge — conflict is a warn banner, not
  a merge engine.
- No draft sharing between users.
- No offline queue beyond the single-payload localStorage mirror.
- No new runtime dependency; reuse existing primitives, tokens, and the Celery beat already present.
- Draft-recovery never creates or mutates a business record to represent progress.
