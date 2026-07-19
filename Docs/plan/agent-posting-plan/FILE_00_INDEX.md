# Agent Posting Actions Plan — widen the assistant's write surface from drafts to posts

**Design session: 2026-07-19.** This is the deliberate reopening of the "posting actions" question
deferred in `agent-actions-plan/FILE_06_ACCEPTANCE_done.md` (Option A vs Option B, recorded in
`DECISIONS.md` "Agent actions — drafts-only standing decision reaffirmed"). Full brainstorm
transcript context lives in this session's history; this file is the resulting spec.

## Why this exists now, and what changed from the original Option B

The original Option B text required "the FILE_05 self-verification pass live first" — that is
`ai-reliability-roadmap/FILE_05_PHASE5_AGENT_ORCHESTRATION.md`, an unbuilt multi-month engine
(durable `AgentRun`/`AgentStep`, typed plan→validate→execute→verify, AI numeric cross-check) that
itself depends on Phase 4 (memory), also unbuilt. Only Phases 1–2 of that 8-phase roadmap are done.

**Founder decision (2026-07-19): proceed WITHOUT waiting for FILE_05.** Ship posting actions now
with **manual guards only** — an org-wide setting (off by default) + the same per-action role check
every draft action already has + a stronger "retype the value" confirm card for post-risk actions.
Explicitly accept the tradeoff: no AI cross-check of numbers before a post card is shown. Revisit
adding the AI self-verify layer as a pure enhancement once FILE_05 ships — it slots in without
changing this plan's action registry or guard shape.

**This supersedes, for these 5 actions only, the "needs FILE_05 first" precondition** recorded in
`DECISIONS.md`. That entry gets a new dated addendum, not a rewrite (the original reasoning was
sound at the time; this is a deliberate, explicit re-decision, not a correction of an error).

## The one hard rule this plan inherits (do not break it)

Every other action-framework rule from `agent-actions-plan/FILE_00_INDEX.md` still applies
unchanged: `requires_confirm=True` on every action (enforced at import by `_validate_action`),
`build_proposal`/`execute` run as the actor (never a privilege the human lacks), every executed
action writes `audit.record(module="assistant", ...)`, money is integer minor units end to end.

**What's different from the drafts-only track:** these 5 actions have `risk="post"` and their
`effects` declare `gl="posts"` and/or `stock="moves"` — which `_validate_action` already requires
to carry at least one invariant (built forward-looking in os-foundations, unused until now). No
action here has a `compensation` — reversal is human-only, on the normal module screen, exactly
like a destructive action with no auto-undo (reverse the journal, cancel the PO, etc. — all already
exist as manual actions; this plan does not add new ones).

## The guard mechanism (shared by all 5 — built once, in FILE_01)

1. **`OrgPreferences.assistant_posting_enabled`** (new boolean field, default `False`) — same
   single-row, System-Admin-only-editable model that already carries `einvoice_enabled`. One new
   checkbox row on `Settings → Organization` (`OrganizationPage.tsx`), same pattern, no new page.
   Off → calm refusal at both `build()` and `execute()`: *"Posting actions aren't turned on for
   this workspace. Ask your System Admin to enable them in Settings → Organization."*
2. **Per-action role check** — identical to how every existing draft action gates itself
   (`_can(actor, <roles>)`), using the SAME roles that gate the manual button for that transition
   (verified per action below — no new permission-code layer).
3. **The underlying domain function's own checks** run as normal and are never bypassed
   (`ApprovalLimitExceededError`, `ClosedPeriodError`, non-postable-account, etc. — inherited free).
4. **Typed re-confirm** — any action with `risk="post"` returns an extra `challenge: {label, minor}`
   key from `build_proposal`. `ActionCard.tsx` renders a text input (reusing the same
   `parseToMinor` client-side match check `PaymentDialog.tsx` already uses); Confirm stays disabled
   until it matches. The confirm endpoint (`erp/assistant/api/views.py`) independently re-validates
   server-side against the value stored in `message.meta.proposal` — the client check is UX only.
   A mismatch returns 400 and **does not consume the card** (single-use is reserved for a real
   confirm, not a typo).

## The 5 actions — verified against real code before this design was written

| # | Action | Target function | Manual precedent | Role gate | `kind` | Notable |
|---|---|---|---|---|---|---|
| 1 | `post_journal_entry_draft` | **new** `post_draft_journal_entry()` | **none — see below** | ACCOUNTANT / BRANCH_MANAGER | `post` | new domain code + new manual "Post" button (parity) |
| 2 | `receive_purchase_order` | `erp/purchasing/services/orders.py` `receive_order()` | `receivePO()` button | BRANCH_MANAGER | `update` | stock effect |
| 3 | `pay_purchase_order` | `orders.py` `pay_order()` | `payPO()` button | BRANCH_MANAGER | `post` | GL effect |
| 4 | `approve_purchase_request` | `erp/purchasing/services/requests.py` `approve_request()` | `approveRequest()` button | BRANCH_MANAGER | `approve` | no money amount — challenge uses request subtotal |
| 5 | `issue_stock_entry` | `erp/inventory/services/stock.py` `issue_stock()` | `issueStock()` in `api/inventory.ts` | BRANCH_MANAGER | `adjust` | stock + GL (COGS) effect |

**Discovered gap (action 1):** the assistant has drafted unposted journal entries since
ai-workspace FILE_10 (`EntryStatus.DRAFT`), but no code path anywhere — manual or API — has ever
posted that draft. `post_journal()` only creates-and-posts fresh from raw line input; it does not
take an existing draft entry and flip its status. `JournalDetailPage.tsx` has no lifecycle button
("a posted journal is read-only — no lifecycle primary"). **Decision (2026-07-19): build both** —
a new `post_draft_journal_entry(entry, actor)` service (re-validate period/accounts since the draft
may be stale, flip status, stamp `posted_at`/`posted_by`, same audit+event as `post_journal`) wired
to BOTH a new manual "Post" button on `JournalDetailPage.tsx` AND the assistant action. Keeps
"AI runs as the user" true — no assistant-only capability.

## Files (each = ONE session; strict order)

| File | Session | Model | Scope |
|---|---|---|---|
| FILE_01 | Guard infrastructure | **Opus** (safety-critical shared foundation — every later file depends on this being right) | `OrgPreferences.assistant_posting_enabled` + serializer + `OrganizationPage.tsx` checkbox; generic `challenge`/typed-confirm plumbing in `actions.py` + confirm endpoint + `ActionCard.tsx` (no new actions registered yet — proven with a test-only toy action, same pattern `test_actions.py` already uses for `_toy_action`) |
| FILE_02 | Post journal entry draft | **Opus** (new GL-affecting domain code, same caliber as agent-actions FILE_04) | `post_draft_journal_entry()` service, manual "Post" button on `JournalDetailPage.tsx`, `post_journal_entry_draft` assistant action |
| FILE_03 | Receive purchase order | **Sonnet** (pattern replication over a real existing endpoint) | `receive_purchase_order` action |
| FILE_04 | Pay purchase order | **Sonnet** | `pay_purchase_order` action |
| FILE_05 | Approve purchase request | **Sonnet** | `approve_purchase_request` action |
| FILE_06 | Issue stock entry | **Sonnet** | `issue_stock_entry` action |
| FILE_07 | Acceptance + bench wiring + DECISIONS.md addendum | **Opus** (judgment + a founder decision to close) | Full FILE_06-shape acceptance checklist (agent-actions precedent) run against all 5 + the 2 new checks (org-toggle-off refusal, retype-mismatch handling); benchmark wiring per the original coordination note; DECISIONS.md addendum recording this plan's outcome |

FILE_03–06 are pattern-replication once FILE_01–02 land — say so at session start and let the
founder `/model` down to Sonnet before burning Opus. FILE_01/02/07 stay on Opus.

## Before you start ANY file in this plan

1. Read `agent-actions-plan/FILE_00_INDEX.md` and `FILE_06_ACCEPTANCE_done.md` in full — this plan
   is its direct sequel and inherits every rule not explicitly changed above.
2. Read `erp/assistant/services/actions.py` end to end — same as the original plan required.
3. Read the target module's real transition function (table above) — never invent a contract.
   FILE_01 additionally reads `erp/identity/models.py` `OrgPreferences` + `OrganizationPage.tsx`'s
   `einvoice_enabled` row as the exact template for the new toggle.
4. Read `apps/web/src/assistant/ActionCard.tsx` and `apps/web/src/components/PaymentDialog.tsx`
   (the existing `parseToMinor` retype-match precedent) before touching the confirm-card UI.

## Per-session protocol (same as EXECUTION_ORDER + agent-actions-plan)

Do the tasks → run the smoke test → gates (`pytest erp/assistant erp/identity` + whichever module
the file touches; any UI string also needs `node scripts/check-i18n-parity.mjs` +
`npx tsc --noEmit` + `python scripts/gates/gate03.py`) → commit (reference the file) → rename
`_done` → update `erp-status` → tell the founder to start a fresh session for the next file.
One file = one session.

## Coordination

- Queue placement: inserted as position **PA** in `EXECUTION_ORDER.md`, directly after the now-done
  **★** (agent-actions-plan) — off critical path (does not block customer handover), founder-paced,
  may be pulled to NEXT ahead of the numbered queue same as ★ was.
- Only file overlap with other in-flight plans: `erp/assistant/services/actions.py` (agent-actions
  precedent: earlier-queued session wins, later rebases) and `JournalDetailPage.tsx` (check
  `git log` for recent touches before FILE_02 — no other plan currently targets it).
- If `ai-reliability` FILE_05 lands before this plan starts (unlikely, but check `erp-status`): the
  self-verification layer becomes an ADDITIVE enhancement to the existing action registry, not a
  redesign — nothing in FILE_01–07 needs to change shape.
