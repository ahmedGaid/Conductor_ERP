# D5 — Security

> Written in normal prose deliberately (security = auto-clarity). Owner of Phase 1 is the
> existing `Docs/plan/00-security-hardening.md` (data-scope leak, SSRF, auth hardening) — it
> was written 2026-07-02 and MUST be re-anchored against today's code before execution.
> AI-layer guardrails belong to `Docs/plan/ai-reliability-roadmap/` (guardrails/security
> phase) — not duplicated here. Multi-tenant isolation lives in D2.P3 (leak tests are part
> of that work by construction).

---

## Phase D5.P1 — Known-issues hardening (owner: plan 00)

### D5.P1.T1 — Re-anchor and execute security-hardening plan 00
**Status:** todo · **Model:** Opus
**Objective:** Execute `00-security-hardening.md` in full against the current codebase: close the data-scope leak, remove SSRF vectors, and harden authentication as that plan specifies.
**Rationale:** These are known, written-down issues. Every week they stay open they compound: more endpoints inherit the leaky pattern, and multi-tenancy (D2.P3) is explicitly blocked on data-scope being real.
**Prerequisites:** none — this outranks feature work at the next queue gap. Read plan 00 fully first; where its snippets contradict live code, its intent wins over its literal text (EXECUTION_ORDER drift rule).
**Steps:** 1. Read plan 00. 2. Verify each named issue still reproduces (write the failing test FIRST for each). 3. Fix per plan. 4. Sweep for the same pattern elsewhere with codegraph (every fix gets a "where else?" pass). 5. Record any scope changes in DECISIONS.
**Architecture decisions:** per plan 00; deny-by-default extended to data scope everywhere.
**Affected files:** per plan 00 findings + the failing-test files added in step 2.
**Acceptance criteria:** every issue in plan 00 has a regression test that failed before the fix and passes after; no endpoint returns data outside the caller's scope in the scope test suite.
**Testing:** `pytest erp` full suite plus the new regression tests; manual verification of one SSRF vector attempt.
**DoD:** gates green, plan 00 renamed `_done`, status flipped, `erp-status` updated.

## Phase D5.P2 — Platform hardening baseline

### D5.P2.T1 — HTTP security headers + CSP
**Status:** todo · **Model:** Sonnet
**Objective:** Strict security headers on all responses: CSP (no external sources — matches the no-CDN brand rule, so this is cheap), `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`/`frame-ancestors`, HSTS (config-gated for prod), and secure cookie flags.
**Rationale:** Baseline web hardening; the customer-hosted deployment story means we cannot rely on a managed edge to add these.
**Prerequisites:** none.
**Steps:** 1. Middleware or settings-level headers in the Django settings module (locate via codegraph). 2. CSP starts `default-src 'self'` and is tightened per real violations found while browsing the app with the console open. 3. Document each header and why in `Docs/patterns/security.md` (create). 4. Test asserting headers on a sample of endpoints.
**Architecture decisions:** CSP report-only mode for one session first, then enforce; no third-party report collector (log locally).
**Affected files:** Django settings/middleware, `Docs/patterns/security.md` (new), `erp/core/tests/test_security_headers.py` (new).
**Acceptance criteria:** headers present on API and app responses; app fully functional under enforced CSP in both themes and languages.
**Testing:** header test green; manual browse of the five main pages with console open showing zero CSP violations.
**DoD:** gates green, status flipped.

### D5.P2.T2 — Secrets policy + startup validation
**Status:** todo · **Model:** Sonnet
**Objective:** All secrets come from environment variables only; a startup check fails fast (clear message, no traceback wall) when a required secret is missing or is a known placeholder; `.env.example` documents every variable; a gate greps the tree for accidentally committed secrets patterns.
**Rationale:** ETA integration (D1.P3.T1) and future WhatsApp/payment integrations multiply the secret count; one committed key can end the company's trust story.
**Prerequisites:** none.
**Steps:** 1. Inventory current settings-read secrets via codegraph. 2. Central `erp/core/env.py` typed accessor with required/optional declaration. 3. `.env.example` complete. 4. Gate: regex scan for key-like strings (`AKIA`, `-----BEGIN`, long base64 assigned to *_KEY/_SECRET) excluding allowlisted test fixtures. 5. Document rotation steps per secret in `Docs/patterns/security.md`.
**Architecture decisions:** no secrets manager dependency yet (DECISION-GATED when cloud lands); env-only is the contract.
**Affected files:** `erp/core/env.py` (new), settings module, `.env.example`, `scripts/gates/gate17.py` (new), security pattern doc.
**Acceptance criteria:** missing required secret aborts startup with a one-line actionable error; gate catches a planted fake key.
**Testing:** startup with stripped env in a subprocess test; gate plant-test.
**DoD:** gates green, status flipped.

### D5.P2.T3 — Rate limiting + brute-force lockout
**Status:** todo · **Model:** Sonnet
**Objective:** Login and password endpoints rate-limited per account and per IP with exponential backoff; a generic per-user API request ceiling; all limits configurable, all limit events audited.
**Rationale:** Public SaaS exposure (Phase F) is coming; auth endpoints are attacked first. Must exist before any internet-facing deployment.
**Prerequisites:** D5.P1.T1 (auth hardening done first so limits wrap the final auth code).
**Steps:** 1. Locate auth endpoints (`erp/identity`). 2. Implement a small fixed-window limiter on the Django cache backend (`erp/core/ratelimit.py`) — no new dependency. 3. Apply decorators: login 5/min/account with backoff, API default 300/min/user (config). 4. 429 responses use the standard error envelope with a blame-free, actionable message in both languages. 5. Audit lockout events.
**Architecture decisions:** cache-backend-based (works single-node today; Redis swap is config when cloud lands); never rate-limit by IP alone for authenticated traffic (NAT-heavy Egyptian ISPs).
**Affected files:** `erp/core/ratelimit.py` (new), identity api modules, locales, `erp/identity/tests/test_ratelimit.py` (new).
**Acceptance criteria:** sixth login attempt within a minute is rejected with 429 and audited; normal API usage never trips the default ceiling in the test scenario.
**Testing:** `pytest erp/identity -k ratelimit`; manual login-hammer check in dev.
**DoD:** gates green, status flipped.

### D5.P2.T4 — Upload validation + audit-log immutability
**Status:** todo · **Model:** Sonnet
**Objective:** Every file upload path enforces an extension+MIME+size allowlist and stores outside the web root with generated names; audit records become append-only (no update/delete grants; DB trigger rejects mutation).
**Rationale:** Attachments and import files are the main untrusted-input surface; the audit trail is only evidence if it provably cannot be edited.
**Prerequisites:** none.
**Steps:** 1. codegraph: all upload endpoints (attachments, imports, assistant files). 2. Shared validator in `erp/core/uploads.py`; apply everywhere; reject with envelope errors. 3. Migration adding an audit-table trigger rejecting UPDATE/DELETE. 4. Tests for both.
**Architecture decisions:** no antivirus scanning dependency (DECISION-GATED for cloud phase); validation is allowlist-only, never blocklist.
**Affected files:** `erp/core/uploads.py` (new), upload endpoints, `erp/audit/migrations/NNNN_append_only.py` (new), tests in touched apps.
**Acceptance criteria:** disguised executable rejected on every upload path; direct SQL UPDATE on an audit row raises.
**Testing:** pytest for each path; raw-SQL mutation attempt test.
**DoD:** gates green, status flipped.

### D5.P2.T5 — Dependency audit gate
**Status:** todo · **Model:** Haiku — DECISION-GATED (dev-dep: pip-audit)
**Objective:** `pip-audit` + `npm audit` (high+ severity) run as a warn-level gate with a documented triage routine; failing advisories become tasks, never silent ignores.
**Rationale:** Low-dependency policy keeps this list short — auditing it is nearly free and closes the supply-chain question customers ask.
**Prerequisites:** DECISIONS entry for pip-audit (dev-only).
**Steps:** 1. Entry. 2. Gate script invoking both, parsing severity, allowlist file with expiry dates per accepted advisory. 3. CONTRIBUTING note on triage.
**Affected files:** `scripts/gates/gate18.py` (new), allowlist, CONTRIBUTING.
**Acceptance criteria:** gate runs clean or lists advisories with owners; expired allowlist entries fail the gate.
**Testing:** run gate; plant expired allowlist entry.
**DoD:** gates green, status flipped.

## Phase D5.P3 — Process & posture

### D5.P3.T1 — Threat model document
**Status:** todo · **Model:** Opus
**Objective:** `Docs/THREAT_MODEL.md`: assets (ledger integrity, customer PII, credentials, audit trail, AI tool surface), actors, entry points, trust boundaries (browser↔API, API↔DB, assistant↔tools, imports↔parsers, ETA/webhooks↔outside), top abuse cases with current control mapping and gaps → each gap becomes a task appended to this file.
**Rationale:** Security work without a model is whack-a-mole; investors and enterprise customers ask for exactly this document.
**Prerequisites:** D5.P1.T1 done (so the model reflects fixed state, not known holes).
**Steps:** 1. Enumerate boundaries from ARCHITECTURE.md + codegraph. 2. STRIDE-style pass per boundary, kept concrete to THIS system. 3. Gap table → append tasks. 4. Review with founder; log adoption in DECISIONS.
**Affected files:** `Docs/THREAT_MODEL.md` (new), this file (appended tasks), DECISIONS.
**Acceptance criteria:** every trust boundary has at least one documented abuse case with its control or a filed task; founder sign-off recorded.
**Testing:** n/a (doc), but each filed gap task carries its own tests.
**DoD:** committed, status flipped.

### D5.P3.T2 — Incident response runbook
**Status:** todo · **Model:** Sonnet
**Objective:** `Docs/runbooks/incident-response.md`: severity levels, first-hour checklist (contain, preserve evidence, assess scope via audit trail), customer notification templates (Arabic first, blame-free but honest), key rotation steps per secret, post-incident review template.
**Rationale:** The trust brand means an incident handled badly is fatal; the runbook is written on a calm day or not at all.
**Prerequisites:** D5.P2.T2 (rotation steps exist to reference).
**Steps:** write it; dry-run once against a tabletop scenario (fake leaked API key) and record the gaps found.
**Affected files:** `Docs/runbooks/incident-response.md` (new).
**Acceptance criteria:** tabletop dry-run completed; every step executable without improvisation.
**Testing:** the tabletop IS the test; note results in the doc footer.
**DoD:** committed, status flipped.
