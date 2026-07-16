# Conductor ARP — Twenty Harvest — Master Index

## Project Goal

Land the 20 improvements harvested from the Twenty CRM comparison (2026-07-16, full report in
that session's chat; summary below) — the habits and features that make Twenty feel world-class
and that FIT the ARP strategy. Split by importance into three tiers:

- **Tier 1 — Ship-safety (FILE_01–07):** versioned releases + upgrade command + upgrade/API
  gates, Playwright E2E regression, outbound webhooks, saved views. Protects the first live
  customer. Directly serves the delivery track's goal.
- **Tier 2 — World-class feel (FILE_08–13):** ⌘K as action surface, human-approval workflow
  node, AI-agent workflow node, custom fields (fields only, never objects), record activity
  timeline.
- **Tier 3 — Steady polish (FILE_14–20):** API keys + docs, Arabic user guide, empty-state
  taxonomy + skeletons + shortcut cheatsheet, inline edit + peek audit, CRM kanban, admin/system
  panel, AI cost visibility.

What Twenty does that we deliberately REFUSED (strategy §5 — do not let sessions pull these in):
metadata engine / custom objects, dashboard builder + IFRAME widgets, GraphQL, app
marketplace/SDK/CLI, email+calendar sync, Stripe/SSO/enterprise machinery, 28 locales.
Routed to existing roadmap phases instead of duplicated here: agent-with-role identity +
agent monitor productization → arp-roadmap Phase C / ai-reliability FILE_03–08; skills-as-data
→ Phase B2; MCP server endpoint → Phase C-adjacent (needs its own claims/permission story);
SSE live lists → deferred (Hard, impact 6 — revisit after Tier 2).

> **Staleness note (deliberate):** written 2026-07-16, ahead of its queue turn. Snippets are
> interface-level BY DESIGN; the EXECUTION_ORDER drift rule applies with full force — the
> "Before You Start" reads are mandatory, intent wins over literal snippet, note drift in the
> commit. Several sessions OVERLAP shipped linear-polish work (peek, views, ⌘K bridge) — those
> sessions AUDIT first and EXTEND, never duplicate.

## Architecture decisions (locked at planning; re-confirm only if code contradicts)

1. **Versioning is a product surface.** `VERSION` at repo root is the single source; exposed in
   settings, `/health`, `/system-check`, and the UI. Releases are git tags `vX.Y.Z` + a
   `CHANGELOG.md` entry. Customer-hosted means upgrades are OUR product, not the customer's risk.
2. **Upgrade = `manage.py upgrade`, idempotent, ordered.** Django migrations PLUS a per-version
   data-fix step registry (`erp/core/upgrades/`), Twenty-style (`2-16/…` ordered commands).
   Applied steps recorded in a table; re-run is a no-op; failure halts with an actionable error.
3. **Gates grow, not sessions' scope:** gate16 = cross-version upgrade drill (restore previous
   release dump → upgrade → health + trial balance intact); gate17 = DRF API schema snapshot,
   additive-only (breaking change fails the gate).
4. **New dependencies are STOP-gates, not assumptions.** Playwright (FILE_04) requires a written
   DECISIONS entry BEFORE install (team rule 7). If refused, the file's fallback applies.
5. **Every write still goes through module service contracts** — webhooks only OBSERVE core
   events; inline edit, kanban drag, custom-field values, approval decisions all mutate via
   existing service fns. No second write path, ever.
6. **The six ARP mechanics hold** (STRATEGY §3): AI node runs as the triggering actor; a write
   action in a workflow is ALWAYS followed by a human-approval node (validator-enforced);
   numbers on the AI cost page are click-verifiable; blockers actionable; resume preserved.
7. **Custom FIELDS, never custom objects.** Definitions per core entity + one JSONB
   `custom_data` column; validation in service contracts; no dynamic tables, no dynamic API.
   Configurability is Odoo's disease — this is the vaccine dose, not the disease.
8. **Money = integer minor units** everywhere new (webhook payloads, custom money fields,
   AI cost page). Format only at the edge (`lib/money.ts`).
9. **Arabic-first**: every new surface designed RTL-first; one canonical Arabic word per concept
   — new terms enter Identity System §6 BEFORE they ship (candidates flagged per session).

## Session Map

| # | File | What gets built | Model | Est. |
|---|---|---|---|---|
| — | **TIER 1 — SHIP-SAFETY** | | | |
| 01 | FILE_01_RELEASE_VERSIONING.md | VERSION source of truth + CHANGELOG + version in health/system-check/UI + tag discipline | Sonnet | 20 min |
| 02 | FILE_02_UPGRADE_COMMAND.md | `manage.py upgrade`: migrate + per-version data-fix registry, idempotent, recorded | Opus | 30 min |
| 03 | FILE_03_UPGRADE_DRILL_GATES.md | gate16 cross-version upgrade drill + gate17 API schema snapshot (breaking-change gate) | Opus | 30 min |
| 04 | FILE_04_E2E_PLAYWRIGHT.md | **DECISIONS gate** → Playwright suite encoding the delivery-track E2E drives | Opus | 30 min |
| 05 | FILE_05_WEBHOOKS.md | Outbound webhooks: subscriptions + signed delivery + retries + settings UI + delivery log | Opus | 30 min |
| 06 | FILE_06_SAVED_VIEWS_BACKEND.md | AUDIT linear-polish views first → SavedView model/service/API (filters/sort/columns, shareable) | Sonnet | 25 min |
| 07 | FILE_07_SAVED_VIEWS_UI.md | View tabs on unified tables: save/rename/share/default, per-page active view | Opus | 30 min |
| — | **TIER 2 — WORLD-CLASS FEEL** | | | |
| 08 | FILE_08_COMMAND_MENU_ACTIONS.md | ⌘K becomes an action surface: context-aware record actions + AI entry + recents | Opus | 30 min |
| 09 | FILE_09_APPROVAL_NODE.md | Human-approval node in the workflow engine + canvas (halt → notify → decide → resume) | Opus | 30 min |
| 10 | FILE_10_AI_AGENT_NODE.md | Assistant tool-action as a workflow node, drafts-only, approval-node-enforced | Opus | 30 min |
| 11 | FILE_11_CUSTOM_FIELDS_BACKEND.md | CustomFieldDef + JSONB values on customers/items, service-contract validation, export | Opus | 30 min |
| 12 | FILE_12_CUSTOM_FIELDS_UI.md | Settings CRUD for field defs + rendering in forms/tables/saved views | Opus | 30 min |
| 13 | FILE_13_ACTIVITY_TIMELINE.md | "النشاط" tab on record pages from the immutable audit trail, humanized ar/en | Sonnet | 25 min |
| — | **TIER 3 — STEADY POLISH** | | | |
| 14 | FILE_14_API_KEYS_DOCS.md | Role-bound API keys + settings→developers page + static API reference page | Sonnet | 25 min |
| 15 | FILE_15_ARABIC_USER_DOCS.md | In-app task-based user guide (ar-first) + glossary from Identity System §6 | Sonnet | 30 min |
| 16 | FILE_16_UX_STATES_BATCH.md | Empty-state taxonomy (no-data/no-match/no-permission) + per-pane skeletons + `?` cheatsheet | Sonnet | 30 min |
| 17 | FILE_17_LIST_UX.md | Inline cell editing on the table kit + side-panel peek gap audit/extension | Opus | 30 min |
| 18 | FILE_18_KANBAN_PIPELINE.md | CRM leads kanban by stage, drag = service-contract stage change, RTL-correct | Opus | 30 min |
| 19 | FILE_19_ADMIN_PANEL.md | Read-only system panel: health, queues, version, env NAMES, flags, backup status | Sonnet | 25 min |
| 20 | FILE_20_AI_COST_PAGE.md | AI usage/cost page over the reliability-gateway budget data, click-verifiable | Sonnet | 20 min |
| 21 | FILE_21_ACCEPTANCE.md | Full acceptance + regression + gates + DECISIONS entries + sign-off | Opus | 30 min |

Merge checkpoints (`---` tier boundaries): after **07** (Tier 1 — the handover-safety merge),
after **13** (Tier 2), after **21** (Tier 3 + acceptance). The founder may PAUSE the plan at any
tier boundary and let the queue move on — tiers are designed as clean exits.

## Affected files (exhaustive at planning time; verify at build time)

Backend:
- New: `VERSION`, `CHANGELOG.md`, `erp/core/upgrades/` (+ registry + steps), 
  `erp/core/management/commands/upgrade.py`, `erp/notifications/webhooks*` (models/service/tasks),
  `erp/core/views_models` or `erp/core/saved_views.py` (SavedView), custom-fields models/service
  in `erp/core/custom_fields.py` + JSONB columns via migrations on `sales.Customer`,
  `inventory.Item`, `erp/identity/api_keys.py`, timeline read-API over `erp/audit`
- Extend: `erp/workflow/` (two node types + validator), module service contracts (custom-field
  validation hook, inline-edit PATCH paths), `config/settings/*` (version), `scripts/gates/`
  (gate16, gate17, `_run.py`), `Docs/RUNBOOK.md` (release + upgrade + e2e procedure)

Frontend (`apps/web/src/`):
- Extend: ⌘K module, unified table kit (view tabs, inline edit), workflow canvas nodes,
  record pages (timeline tab), settings pages (developers/system/AI/fields), `help/`,
  empty-state + skeleton components, `i18n/locales/ar.json` + `en.json`
- New: `pages/settings/…` per session, `api/…` clients per session, `e2e/` (Playwright, gated)

## Never touch

- `erp/audit/models.py` — append-only; timeline READS via `erp/audit` services only
- Existing module service write-path signatures — new callers CALL them, never modify them
- `apps/web/src/styles/tokens.css` (no new raw hex) · `apps/web/src/app/icons.tsx` (own icons only)
- The assistant event protocol and reliability-gateway internals (FILE_10/20 consume, not change)
- **No new npm or pip dependencies without a written DECISIONS entry first** (Playwright included)

## Ground Rules (every session)

1. **Read before write** — the named reads, literally; code drift → intent wins, note it.
2. **Additive** — nothing existing breaks; every module keeps working untouched.
3. **Overlap discipline** — linear-polish shipped peek/views/⌘K-bridge in some form: sessions
   06/07/08/17 START by auditing what exists and extend it. Duplicating a shipped primitive is
   a failed session.
4. **Frontend hard rules** — tokens only, logical CSS, ar/en parity, designed
   empty/error/loading states, monochrome chrome, settled motion, human blame-free errors.
5. **Every AI-touching session ships its permission story** (team rule 9) — who triggers, what
   it can touch, what the audit shows, in the commit/PR description.
6. **Gates before "done"** — `apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc -b`;
   repo root: `python scripts/gates/gate03.py`; backend: `pytest erp/<touched app>`. UI sessions
   also run the `conductor-brand` brand-feel checklist.
7. **Done means renamed** — green + committed → rename the file with `_done`.

## How to use this plan

1. New Claude Code session → load this index + the next `FILE_NN` (lowest number without `_done`).
2. Model check (Model column above) → suggest `/model` switch in one line if Sonnet fits.
3. Do the reads → tasks → smoke test → gates → commit → rename `_done` → update `erp-status`
   → tell the user to start a fresh session. One file = one session.

## After all sessions complete

- FILE_21 acceptance in both languages (ar RTL first) against the seeded dev environment.
- DECISIONS.md entries: versioning/upgrade scheme, Playwright (or its refusal + fallback),
  webhook SSRF posture, custom-fields scope boundary (fields-only forever), saved-views sharing
  model.
- Update the `erp-status` skill; new Arabic terms logged in Identity System §6; RUNBOOK carries
  the release + upgrade drill procedure.

*Generated by ag-plan skill. Do not edit this index manually.*
