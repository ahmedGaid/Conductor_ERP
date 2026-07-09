# Phase 8 (Months 22–24) — Production Hardening & Continuous Evaluation

## Objectives

1. Prompt and model changes ship like code ships: staged rollout, automatic quality gate,
   one-command rollback.
2. Quality drift is detected by machines on a schedule, not by users on a bad day.
3. Operations are boring: alerting on the four golden signals of the AI layer (errors, latency,
   cost, quality), runbooks for every failure class, kill switches that actually kill.
4. The whole 24-month program closes with a full acceptance: every blocking suite green, every
   SLO held for 30 consecutive days, sign-off recorded.

## Architecture decisions

- **Canary by deterministic assignment, not infrastructure.** A prompt/model change registers as
  a `Variant` (prompt_ref or routing override + rollout %); the gateway assigns by stable hash of
  user id → variant. No second deployment, no feature-flag service — a table and a hash. Traces
  record the variant; the eval harness + live metrics compare arms.
- **Auto-rollback is conservative:** a variant that underperforms its guardrail metric (eval
  score on the shadow set, error rate, or explicit-negative-feedback rate) auto-reverts to 0% and
  notifies — it never auto-promotes. Promotion is a human commit, informed by the comparison
  report. Machines pull back; humans push forward.
- **User feedback becomes a metric stream:** the existing message actions gain a thumbs-down with
  an optional reason chip (wrong / unclear / slow / unsafe — ar/en). Negative-rate per feature per
  variant joins the drift dashboard. Prefill edit-rate (how much users correct AI-drafted fields)
  is computed from existing action payloads — the honest quality signal for the agentic flows.
- **Runbooks live in the repo** (`Docs/ops/runbooks/`), one file per failure class, each with:
  detection signal, impact statement, first response, kill switch, escalation, post-incident rule
  (attack corpus / golden set gets a case). Tested by drill, not by faith.
- **Kill switches are layered:** global `ASSISTANT_ENABLED` (exists) → per-feature flags
  (`ASSISTANT_FEATURES` set: chat, agent, actions, knowledge, memory, workflows) → per-variant 0%.
  Each documented in the runbooks with blast radius.

## Decision points

- None. Closing phase uses only what the program built.

## Success metrics (phase exit = program exit)

- One full canary cycle executed on a real prompt change: staged 5% → 50% → 100% with comparison
  reports at each stage, plus one rehearsed auto-rollback.
- Drift job running weekly for ≥ 8 weeks with ≥ 1 true regression caught in rehearsal (seeded).
- All blocking suites (leakage, scope fuzz, attack corpus, unsafe-write) green in CI as hard gates;
  golden eval threshold now BLOCKING at Month-24 targets (FILE_00 table).
- 30 consecutive days: TTFT/latency SLOs held, error rate < 1%, zero critical incidents, cost
  within budget envelope. Sign-off document committed.

---

## Tasks

### [ ] T8.1 — Variant registry + canary assignment

- **Goal:** prompt/routing changes can roll out to a % of users with full trace attribution.
- **Prereq:** Phase 7 done.
- **Files:** models migration (`assistant_variant`); modify `gateway/core.py`,
  `services/prompt_registry.py`.
- **Steps:**
  1. `Variant`: id, kind (`prompt` | `routing`), target (prompt id | task class), payload
     (prompt_ref | model chain), rollout_pct (0–100), status (`active` | `rolled_back` |
     `promoted`), guardrail metric spec (JSON: metric, window, threshold), created_by, timestamps.
  2. Assignment: `hash(user_id, variant_id) % 100 < rollout_pct` — stable per user, independent
     across variants. System jobs (digest etc.) never get variants (deterministic ops).
  3. Gateway/prompt-registry consult active variants at resolve time; `Trace.meta.variant`
     records the assignment (control arm records `control`).
  4. Management commands: `variant_create/adjust/rollback` (no admin UI — variants are operator
     actions, CLI is the calm choice).
- **Accept:** assignment unit tests (stability, distribution ±2% at 10k simulated users);
  trace attribution test; rollback command → next call resolves control.
- **Output:** change ships in slices, not cliff dives.

### [ ] T8.2 — Variant comparison report + auto-rollback watchdog

- **Goal:** every variant gets an evidence report; bad variants pull themselves back.
- **Prereq:** T8.1.
- **Files:** create `evals/variant_report.py`, `management/commands/variant_watch.py`.
- **Steps:**
  1. Report: per arm — trace volume, error rate, latency p95, cost/call, negative-feedback rate
     (T8.4), and offline eval score (golden subset run against the variant's prompt_ref/routing
     via recordings where valid; live shadow subset optional `--yes-live`). Output: one markdown
     file per variant per run in `evals/results/variants/`.
  2. Watchdog command (cron, hourly): evaluates each active variant's guardrail metric over its
     window; breach → set rollout 0%, status `rolled_back`, write the report, notify admins via
     the digest email path. Minimum-volume floor before judging (no rollback on 5 samples).
  3. Rehearsal: seed a deliberately-bad variant in staging (prompt that fails evals) → watchdog
     rolls it back within one cycle — documented drill.
- **Accept:** watchdog unit tests (breach, floor, no-double-rollback); rehearsal documented;
  report renders with real fields.
- **Output:** the blast radius of a bad prompt is one hour and one hash bucket.

### [ ] T8.3 — Weekly drift detection

- **Goal:** quality drift (provider model updates, data shape changes) is caught weekly.
- **Prereq:** T8.2.
- **Files:** create `management/commands/drift_check.py`; extend the weekly report (T1.9).
- **Steps:**
  1. Weekly live shadow-eval (`--yes-live`, budgeted via a dedicated org budget from T2.7):
     fixed 40-case shadow subset of the golden set (rotating 10 to resist overfitting/contamination)
     against the ACTUAL production routing. Compare to the 8-week rolling mean; drop > 3 points →
     alert + auto-file a findings entry; drop > 6 → recommend pinning the previous model version
     in routing (providers silently update — pin syntax documented per provider in the routing
     settings comment).
  2. Data drift: weekly distribution snapshot of trace features (feature mix, envelope sizes,
     tool-call mix, language mix) vs prior month; > 2σ shifts flagged in the weekly report
     (informational — humans interpret).
  3. Rehearsal: seed a degraded recording set → drift alert fires — documented.
- **Accept:** command tests offline (seeded results → correct alerts); rehearsal documented;
  weekly report shows the drift section.
- **Output:** the model changing under you becomes a Tuesday email, not a support fire.

### [ ] T8.4 — Feedback signals: thumbs + edit-rate

- **Goal:** live quality signals flow from real usage into the variant/drift machinery.
- **Prereq:** T8.1 (attribution exists).
- **Files:** models migration (`assistant_feedback`); message-actions UI; api endpoint;
  aggregation into ops + variant reports.
- **Steps:**
  1. Thumbs-down (down only — calm UI, no gamified thumbs-up) on assistant messages with optional
     one-tap reason chips: `wrong | unclear | slow | unsafe` (ar/en). Row: message FK, trace FK,
     reason, comment (optional, redacted at write via T6.4's redactor), timestamps. `unsafe`
     additionally notifies admins immediately (runbook link).
  2. Edit-rate: for confirmed actions born from AI proposals, diff the proposed args vs executed
     args (both already in the action records) → edited-field ratio per action type. Pure
     computation over existing data — verify the payloads suffice; if a field is missing, add it
     to the action record write path (additive).
  3. Both signals: ops view tiles + per-variant columns + weekly report.
  4. Brand-feel checklist on the feedback affordance (it must feel like Linear, not like a survey).
- **Accept:** endpoint + RBAC tests; edit-rate unit test with fixture proposals; i18n parity,
  tsc, gate03; unsafe-path notification test.
- **Output:** users grade the assistant continuously, without being asked to.

### [ ] T8.5 — Alerting on the four golden signals

- **Goal:** breaches page a human through the existing notification path; no silent degradation.
- **Prereq:** T8.3, T8.4.
- **Files:** create `management/commands/ai_alerts.py` (cron, 5-min cadence) +
  `Docs/ops/ai-alerts.md` (thresholds).
- **Steps:**
  1. Signals + thresholds (from BASELINE history, documented): error rate (> 5% over 15 min),
     latency (TTFT p95 > 2× budget over 30 min), cost (daily spend > 150% of trailing-week
     median by 6pm), quality (unsafe feedback ≥ 1, negative rate > 2× mean, drift alert relay).
  2. Delivery: existing digest email path + the admin panel notice surface; each alert carries
     the matching runbook link. Dedup window so one incident = one alert thread, not a storm.
  3. Alert-on-silence: the alert command records a heartbeat; a missing heartbeat > 30 min shows
     in the ops view banner (watching the watchmen, cheaply).
- **Accept:** threshold logic unit-tested with seeded traces per signal; dedup test; heartbeat
  test; thresholds doc committed.
- **Output:** the team hears it before the customer says it.

### [ ] T8.6 — Runbooks + kill switches + drills

- **Goal:** every failure class has a rehearsed response.
- **Prereq:** T8.5.
- **Files:** create `Docs/ops/runbooks/` — one file each: provider-outage, cost-runaway,
  quality-regression, prompt-injection-report, data-leak-report, unsafe-output-report,
  stuck-agent-runs; settings `ASSISTANT_FEATURES` flags.
- **Steps:**
  1. Implement per-feature kill switches: `ASSISTANT_FEATURES` set checked at the API/gateway
     boundary per feature; a killed feature shows its designed "temporarily off" state (ar/en,
     blame-free, with the rest of the assistant still working). Tests per flag.
  2. Write the seven runbooks in the decided format (detection → impact → response → kill switch →
     escalation → post-incident rule). Short, imperative, tested-by-reading: a person who has
     never seen the system must be able to execute one.
  3. Drill two of them for real in staging (provider-outage: revoke key; cost-runaway: seed a
     spend spike) — timestamps + outcomes recorded in each runbook's "last drilled" footer.
- **Accept:** kill-switch tests green; two drill records committed; runbook review by the user.
- **Output:** 3am has a checklist.

### [ ] T8.7 — Gates go blocking (the ratchet)

- **Goal:** the quality bars built over 24 months become hard CI failures.
- **Prereq:** T8.3 stable ≥ 4 weeks.
- **Files:** CI/gate chain config; `evals/` thresholds.
- **Steps:**
  1. Golden eval threshold → blocking at the FILE_00 Month-24 targets (pass ≥ 95%, groundedness
     ≥ 98%); retrieval suite → blocking at Phase 3 exit numbers; agent bench → blocking at Phase
     5 exit numbers.
  2. Already-blocking suites re-confirmed in the chain: leakage (T4.6), scope fuzz (T6.6), attack
     corpus (T6.3), unsafe-write (T5.6), tenant isolation if unlocked (T6.7).
  3. Escape hatch documented: a threshold may be lowered ONLY by a commit that edits the
     threshold file AND adds a dated justification line — no env-var overrides.
- **Accept:** a seeded regression in each newly-blocking suite fails CI (verified once each,
  then reverted); thresholds file committed with the justification protocol header.
- **Output:** quality can only ratchet up.

### [ ] T8.8 — Program acceptance + sign-off

- **Goal:** the 24-month program closes with evidence, not vibes.
- **Prereq:** all phases `_done` except this file; 30-day observation window scheduled.
- **Steps:**
  1. Full-suite run: golden, retrieval, agent bench, attack corpus, leakage, scope fuzz, load
     scenarios — all green at final thresholds; results archived under `evals/results/final/`.
  2. 30-day SLO watch: alerts quiet (or incidents handled per runbook + post-incident cases
     added); daily cost within envelope. Any critical incident resets the 30-day clock.
  3. Write `Docs/plan/ai-reliability-roadmap/SIGNOFF.md`: final metrics vs the FILE_00 table
     (baseline → M12 → M24 actuals), open risks + owners, the standing operational calendar
     (weekly drift, hourly watchdog, quarterly red-team, purge schedule), and the first three
     items of the NEXT roadmap (whatever the 24 months surfaced).
  4. Update the `erp-status` skill anchor; brand-feel checklist pass over every AI surface touched
     since Phase 4 (memory page, workflow picker, feedback affordance, degraded states) — the
     program ends on craft, not just correctness.
  5. Rename this file `_done`. The roadmap folder is now history; SIGNOFF.md is the record.
- **Accept:** SIGNOFF.md committed with real numbers; user sign-off recorded in it.
- **Output:** an AI layer you can put in front of an enterprise buyer's security team — measured,
  guarded, rehearsed, and still calm.
