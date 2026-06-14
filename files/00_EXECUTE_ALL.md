# Master Execution Plan — Graph-Based ERP Workflow Orchestration Layer (MVP)

> **Audience:** an autonomous coding agent (e.g. Claude Code). Execute this **without** asking the
> human for confirmation between phases. Every human "go-ahead" from the original brief has been
> replaced by a **machine gate**: a command that must exit `0` or a test that must pass. If a gate
> fails, fix and re-run the *same* phase until the gate passes; only then advance.

---

## 0. Locked decisions (do NOT re-litigate)

The original brief said "pick one and stay consistent." Those picks are now **made**. Use exactly these:

| Concern | Decision (locked) |
|---|---|
| Backend language/runtime | **Node.js 20 + TypeScript** (strict) |
| Backend framework | **Express 4** + **zod** for request validation |
| Orchestration DB access | **Prisma** (schema, migrations, typed client, transactions) |
| External SQL/PL-SQL adapter driver | **`pg`** (node-postgres) `Pool`, parameterized queries ONLY |
| DB | **PostgreSQL 16** (via `docker-compose`) |
| Tests | **Vitest** (unit + integration), **Playwright** (one e2e in Phase 08) |
| Frontend build | **Vite + React 18 + TypeScript** |
| Graph canvas | **React Flow** (`@xyflow/react`) |
| UI components | **shadcn/ui + Tailwind CSS**, tuned to the tokens in Phase 06 (NOT Base Web) |
| i18n | **i18next + react-i18next**, default locale **`ar`**, fallback **`ar`**, second locale `en` |
| Fonts | **IBM Plex Sans Arabic** (Arabic-first) + **Inter** (Latin) |
| Repo shape | **npm workspaces monorepo**: `apps/api`, `apps/web` |
| Package manager | **npm** |

If any locked decision later blocks you, do NOT silently swap it — leave a `// DECISION-CONFLICT:` comment,
implement the closest working alternative, and record it in `DECISIONS.md` at repo root.

---

## 1. Forbidden list (hard stop — never build these)

Accounting/inventory-valuation logic · any ERP core module as business logic (GL/AP/AR/INV/PO) ·
a full ERP · **any AI/LLM feature** · full BPMN 2.0 compliance · distributed/multi-node execution,
message queues, horizontal-scaling infra · auth beyond the single hardcoded dev user.

If a phase tempts you toward any of these "to make it complete," STOP, do not build it, and write the
temptation into `DECISIONS.md` instead.

---

## 2. Phase order (execute top to bottom, one at a time)

| # | File | Concern |
|---|---|---|
| 00 | `PHASE_00_scaffold_and_gates.md` | Monorepo, tooling, Postgres, the gate runner |
| 01 | `PHASE_01_schema_migrations_seed.md` | 7 tables, migrations, Purchase-Request seed |
| 02 | `PHASE_02_execution_engine.md` | State machine, I/O contract, persist-per-transition, resume, idempotency, retry, edges — **tests first** |
| 03 | `PHASE_03_node_executors.md` | Start / API Call / Approval / Condition / Script / End behind one interface |
| 04 | `PHASE_04_integration_adapters.md` | REST / SQL-PLSQL / Webhook behind one interface + mock ERP |
| 05 | `PHASE_05_backend_api.md` | Workflow CRUD, start instance, submit approval, read logs |
| 06 | `PHASE_06_frontend_foundation.md` | Tokens, Tailwind/shadcn theme, i18n+RTL, fonts, app shell, translation build-gate |
| 07 | `PHASE_07_frontend_screens.md` | Dashboard → list → canvas → node panel → execution viewer |
| 08 | `PHASE_08_reference_use_case_e2e.md` | Wire Purchase-Request flow + verify all success criteria + Playwright e2e |
| 09 | `PHASE_09_cleanup_commit.md` | Lint/typecheck/test sweep, cleanup, git commit + push |

**Rule:** complete one phase fully and pass its gate before starting the next. A phase may be re-run in
isolation (each phase re-reads only the repo state, never the previous phase file).

---

## 3. The global gate runner (built in Phase 00, used by every phase)

Each phase ends with `npm run gate:NN`. Internally a gate is a script under `scripts/gates/` that runs the
concrete checks and exits non-zero on any failure. The agent must run the gate, read the output, and only
advance on exit `0`. There is no human approval step — **the green gate is the approval.**

Top-level convenience:
```bash
npm run gate:00   # ... through ...
npm run gate:09
npm run gate:all  # runs every gate in order; the build is "done" when this exits 0
```

---

## 4. After all phases complete

### Compact
- Remove any debug `console.log` added during implementation (keep the structured logger).
- Remove every `TODO` / `FIXME` that is not tracked in `DECISIONS.md`.
- `npm run lint -- --fix` in both workspaces; ensure no unused imports.

### Verify (the definition of done)
```bash
npm run gate:all
```
This single command must exit `0`. It transitively asserts every box in §5.

### Git
```bash
git add -A
git commit -m "feat: graph-based ERP workflow orchestration layer MVP (engine, adapters, bilingual RTL UI, PR-approval reference flow)"
git push        # if no remote is configured, skip and note it in DECISIONS.md
```

---

## 5. Success criteria (encoded as gates — all must pass under `gate:all`)

- [ ] A user can visually build a workflow and save it. → `gate:07` (canvas save round-trips to DB)
- [ ] That workflow runs end-to-end. → `gate:08`
- [ ] Execution viewer shows step-by-step node-level logs with status. → `gate:07` + `gate:08`
- [ ] At least one real external REST call executes through an adapter. → `gate:08` (calls the mock ERP over HTTP)
- [ ] A manual approval step pauses (`waiting`) and resumes on approve/reject. → `gate:02` + `gate:08`
- [ ] Killing the backend mid-execution and restarting resumes from DB, no lost/dup steps. → `gate:02` (crash-resume test)
- [ ] Retrying an ERP-write node does NOT create a duplicate record. → `gate:02` + `gate:04` (idempotency test)
- [ ] The Purchase Request Approval Flow runs as the seeded reference example. → `gate:01` (seed) + `gate:08` (run)
- [ ] App loads in Arabic/RTL by default; sidebar on the right; tables/cards mirror. → `gate:06`
- [ ] Language switcher flips AR↔EN and RTL↔LTR live, no layout breakage. → `gate:06`
- [ ] No hardcoded UI strings; build fails on a missing translation key. → `gate:06` (i18n key-parity check)
- [ ] Metric cards, status pills, data table, command bar match the reference dashboard in both directions. → `gate:07`
- [ ] Canvas + execution viewer carry the Conductor look and mirror in RTL. → `gate:07`

---

## 6. Engine contract (non-negotiable — Phase 02 enforces, every later phase must respect)

1. **Determinism:** same definition + same inputs + same external responses ⇒ same path + same logged result.
   No wall-clock branching, no random edge ordering. Edges are evaluated in a stable, persisted order.
2. **Node I/O contract:** every executor implements
   `run({ instanceContext, nodeConfig, incomingPayload }) → { status: 'success'|'failed'|'waiting', outputPayload, error? }`.
   Pure function of inputs + one explicitly-declared side effect (the adapter call). No hidden global state.
3. **State machine, not a script:** the instance is persisted after **every** node transition. The process
   may crash between any two nodes and resume from the DB with zero data loss. Never keep execution state only in memory.
4. **Idempotency on ERP writes:** any external-write node carries an idempotency key = `sha256(instanceId|nodeId|attempt)`.
   On retry the adapter must not create duplicates. If idempotency cannot be guaranteed, mark the node `failed`
   and require manual intervention — never silently retry.
5. **Edge evaluation:** a Condition node selects exactly one winning outgoing edge. Zero or multiple winners ⇒ instance halts `failed` with a clear error. Never guess.
6. **Manual/Approval:** set instance `waiting`, persist, exit cleanly. Resume is a separate inbound event
   (approve/reject) re-entering the engine at that node. Approval timeouts are out of MVP scope.

---

## 7. Paste-into-agent block

```
Read _phases/00_EXECUTE_ALL.md, then execute PHASE_00 through PHASE_09 in order.

Rules:
- Do not ask the human for confirmation. The green gate (npm run gate:NN exiting 0) is the approval.
- Complete one phase fully and pass its gate before starting the next.
- If a gate fails, fix and re-run the SAME phase until it passes.
- Never build anything on the forbidden list in §1; if tempted, record it in DECISIONS.md and move on.
- Honor the engine contract in §6 in every phase.
- After PHASE_09, `npm run gate:all` must exit 0, then commit and push.
```
