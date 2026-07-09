# D7 — Infrastructure & DevOps

> Facts today: no CI (`.github/workflows` absent), dev runs on Windows, `erp/monitoring`
> app exists, deployment story = customer-hosted first with cloud multi-tenant later
> (arp Phase F). This domain builds: reproducible dev, CI, packaging, backups, and
> observability — sized for a bootstrap company, upgradeable for cloud.

---

## Phase D7.P1 — Reproducible environments

### D7.P1.T1 — One-command dev stack
**Status:** todo · **Model:** Sonnet — DECISION-GATED only if Docker adopted for dev
**Objective:** the existing `run-dev.ps1` (Django :8000 + Vite :5173 — already live per erp-status) promoted to the documented, complete boot path: migrations + optional seed folded in, a `scripts/dev.sh` POSIX twin, and `Docs/runbooks/dev-setup.md` covering from-zero setup in ≤15 minutes (Postgres 16 service, Redis, venv, Node — the erp-status env facts written down in-repo). `Docs/RUNBOOK.md` exists — reconcile/merge rather than duplicate.
**Rationale:** every new agent/human session and every E2E run pays the boot cost; today the boot facts live in a skill (account-local), not the repo = hidden context for anyone else.
**Prerequisites:** none. Read `run-dev.ps1` + `Docs/RUNBOOK.md` first — extend, don't invent parallel scripts.
**Steps:** 1. Inventory current run steps from erp-status skill + `run-dev.ps1` + RUNBOOK. 2. Extend the script (migrate step, `--seed` flag) + write the POSIX twin. 3. Write/merge dev-setup runbook: prerequisites, env vars from `.env.example`, common failures. 4. Verify from a clean-clone checklist.
**Architecture decisions:** native processes for dev (no Docker requirement on Windows dev machines); Docker enters at D7.P3.T1 for deployment.
**Affected files:** `scripts/dev.ps1` (new), `scripts/dev.sh` (new), `Docs/runbooks/dev-setup.md` (new), CONTRIBUTING link.
**Acceptance criteria:** stack up from one command on this machine; runbook alone suffices on a clean machine.
**Testing:** run the script; walk the runbook checklist.
**DoD:** committed, status flipped, erp-status dev-facts updated to point here.

### D7.P1.T2 — Migration safety policy
**Status:** todo · **Model:** Sonnet
**Objective:** written + gated migration rules: no destructive column drops in the same release as code stops using them (two-step), no data migrations mixed with schema in one file, every migration reversible or explicitly marked irreversible with reason; gate checks new migrations for `RemoveField`/`DeleteModel` without an accompanying `# two-step: verified` tag.
**Rationale:** customer-hosted installs upgrade unattended; a bad migration bricks a paying customer's server with no ops team to rescue it.
**Prerequisites:** none.
**Steps:** 1. Policy section in `Docs/patterns/backend.md`. 2. `scripts/gates/gate20.py` scanning migrations added since a recorded baseline. 3. Baseline file with current migration list.
**Affected files:** pattern doc, `scripts/gates/gate20.py` (new), baseline file, `_run.py`.
**Acceptance criteria:** gate green; planted unsafe migration caught.
**Testing:** plant-test.
**DoD:** gates green, status flipped.

## Phase D7.P2 — Continuous integration

### D7.P2.T1 — GitHub Actions pipeline
**Status:** todo · **Model:** Sonnet
**Objective:** `.github/workflows/ci.yml` on PR + main push: job matrix = backend (Postgres service, `pytest erp`, gate runner) and web (`npm ci`, parity script, `npx tsc --noEmit`, build); required status checks enabled on main.
**Rationale:** gates exist but run on honor system; CI makes the done-bar mechanical for every agent and future hire.
**Prerequisites:** D7.P1.T1 (env documented → CI env derivable). E2E job deferred to T2.
**Steps:** 1. Write workflow (cache pip/npm; Postgres service container; env from repo secrets/`.env.example` non-secret defaults). 2. Make the gate runner CI-friendly (non-zero exit, no interactive bits) — fix if needed. 3. Push, iterate to green. 4. Branch protection: require both jobs. 5. Badge in README, note in CONTRIBUTING.
**Architecture decisions:** one workflow file; matrix not split files; runtime target <10 min (cache aggressively).
**Affected files:** `.github/workflows/ci.yml` (new), possibly `scripts/gates/_run.py` (CI mode), README, CONTRIBUTING.
**Acceptance criteria:** green run on a no-op PR; red run on a planted failing test; merge blocked while red.
**Testing:** the two runs above.
**DoD:** CI green on main, protection on, status flipped.

### D7.P2.T2 — E2E job in CI
**Status:** todo · **Model:** Sonnet
**Objective:** add the Playwright smoke pack (D6.P2.T1) as a CI job: boot stack in the runner, seed, run 6×2 journeys, upload failure screenshots as artifacts.
**Rationale:** the smoke pack only pays off when it runs on every PR.
**Prerequisites:** D6.P2.T1, D6.P2.T3, D7.P2.T1.
**Steps:** compose the job (backend + built web served, or dev servers), wire seed, artifacts on failure, mark required after one week of stability.
**Affected files:** `ci.yml`.
**Acceptance criteria:** green on main twice consecutively; failure uploads screenshots.
**Testing:** plant a broken journey once.
**DoD:** job required, status flipped.

## Phase D7.P3 — Packaging, backup, observability

### D7.P3.T1 — Customer-hosted packaging (Docker)
**Status:** todo · **Model:** Opus — DECISION-GATED (Docker as deployment vehicle; runtime deps pinned)
**Objective:** production packaging: multi-stage Dockerfile (web built + collected static + gunicorn-equivalent WSGI server — server choice in the DECISIONS entry), `docker-compose.customer.yml` (app + Postgres + volume + backup sidecar), versioned releases, one-page install runbook in Arabic and English.
**Rationale:** "customer-hosted premium option" (ARP_STRATEGY §4.8) needs a real artifact, not a repo clone; also becomes the cloud unit later.
**Prerequisites:** D7.P1.T1, D5.P2.T1/T2 (headers + env contract), D7.P1.T2.
**Steps:** 1. DECISIONS entry (WSGI server, image base, versioning scheme). 2. Dockerfile + compose. 3. Entrypoint: migrate-on-boot with lock, env validation (fails fast per D5.P2.T2). 4. Install + upgrade + rollback runbook. 5. Full dry-run on this machine: install → seed → use → upgrade → rollback.
**Affected files:** `Dockerfile` (new), `docker-compose.customer.yml` (new), `scripts/entrypoint.sh` (new), `Docs/runbooks/install-customer-hosted.md` (new, ar+en).
**Acceptance criteria:** dry-run completes: fresh install to working app <30 min; upgrade preserves data; rollback restores prior version + data intact.
**Testing:** the dry-run IS the test; record timings in the runbook.
**DoD:** dry-run recorded, status flipped.

### D7.P3.T2 — Backup + restore drill
**Status:** todo · **Model:** Sonnet
**Objective:** scheduled `pg_dump` (+ uploaded-files dir) backup script with retention, integrity check (restore into scratch DB + `verify_ledger`), and a written restore runbook; drill executed once and timestamped.
**Rationale:** a backup never restored is a hope, not a backup; ledger data is the business.
**Prerequisites:** D7.P3.T1 (backup sidecar slot exists) — script itself has no blocker, do standalone if T1 lags.
**Steps:** 1. `scripts/backup.sh` + retention (7 daily/4 weekly/12 monthly). 2. `scripts/verify_backup.sh`: restore latest into scratch, run `verify_ledger` + row-count sanity. 3. Runbook with RTO/RPO statements (target: RPO 24h customer-hosted, RTO 2h). 4. Execute the drill; record.
**Affected files:** `scripts/backup.sh`, `scripts/verify_backup.sh` (new), `Docs/runbooks/backup-restore.md` (new).
**Acceptance criteria:** drill log shows restore + clean `verify_ledger` on restored data.
**Testing:** the drill.
**DoD:** drill recorded in runbook footer, status flipped.

### D7.P3.T3 — Structured logging + health/readiness endpoints
**Status:** todo · **Model:** Sonnet
**Objective:** JSON-structured request/error logs with correlation id (builds on `erp/core/correlation.py` + `logging.py` — extend, don't replace), `/healthz` (process up) + `/readyz` (DB reachable, migrations current, required env present), wired into `erp/monitoring`.
**Rationale:** first thing an operator (us or the customer's IT) needs when something is wrong; prerequisite for uptime monitoring and cloud orchestration.
**Prerequisites:** none (monitoring app + correlation already exist — verify shape first via codegraph).
**Steps:** 1. Read current `erp/core/logging.py` + `erp/monitoring`. 2. Extend to structured JSON with level, logger, correlation, user id (never PII payloads). 3. Endpoints (unauthenticated healthz; readyz detail behind permission). 4. Log-hygiene test: no secrets/PII patterns in captured logs of a full test run.
**Affected files:** `erp/core/logging.py`, `erp/monitoring/` endpoints, tests.
**Acceptance criteria:** both endpoints behave under a stopped-DB simulation; sample log line parses as JSON with correlation id present across one request's entries.
**Testing:** pytest for endpoints + hygiene scan.
**DoD:** gates green, status flipped.

### D7.P3.T4 — Error tracking decision
**Status:** todo · **Model:** Opus — DECISION-GATED (new dependency and/or external service)
**Objective:** DECISIONS entry: self-hosted-friendly error aggregation (structured-log-based, using existing `erp/monitoring`) vs Sentry SDK (conflicts with no-CDN/customer-hosted privacy unless self-hosted Sentry); implement the chosen minimal path (error events table + daily digest into notifications).
**Rationale:** unknown production errors are unacceptable for the trust brand; but the dependency question is real for customer-hosted privacy.
**Prerequisites:** D7.P3.T3.
**Steps:** 1. Entry with the privacy analysis. 2. Implement chosen path (default recommendation: in-house table + digest now; Sentry re-evaluated at cloud phase). 3. Surface in monitoring UI page if one exists.
**Affected files:** DECISIONS, `erp/monitoring/` (event model, digest task), tests.
**Acceptance criteria:** unhandled exception in dev produces one aggregated event (deduped by stack hash), visible to admin.
**Testing:** raise test exception; assert single event + dedupe on repeat.
**DoD:** gates green, status flipped.
