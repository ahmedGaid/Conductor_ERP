# Post-Handover v1.1 — Master Index ("the rest")

> **Source: QA/handover audit, 2026-07-18 — Phase 1 (Should-Have) + Phase 2 (Nice-to-Have).**
> These close the audit's non-blocking findings. They run AFTER the pre-handover set and the
> handover itself (or interleave once the customer is live). None blocks go-live.

## Scope note — what is NOT duplicated here
Three audit "remaining feature" items already own dedicated plan folders — this plan REFERENCES
them, never re-plans them:
- **Smart Import UI** → `Docs/plan/smart-import-plan/` FILE_12–15,17 (12/17 done).
- **Admin panel + AI cost page** → `Docs/plan/twenty-harvest-plan/` FILE_19, FILE_20, FILE_21.
- **AI reliability Phases 3–8** → `Docs/plan/ai-reliability-roadmap/` FILE_03–08.
This folder holds only the audit findings that had NO existing home: CI/quality-tooling, dependency
hygiene, coverage, frontend test/a11y gaps, cross-platform docs.

## Phase 1 — Should-Have (within 2–4 weeks of handover)

| File | Task | Sev closed | Effort | Model |
|---|---|---|---|---|
| FILE_01 | Enforce ruff + mypy + bandit in CI (installed, not currently gated) | 🟡 Med | Small | Sonnet |
| FILE_02 | Backend dependency lockfile + Dependabot config | 🟡 Med | Small | Sonnet |
| FILE_03 | Backend coverage reporting (pytest-cov) + tracked baseline | 🟡 Med | Small | Haiku/Sonnet |
| FILE_04 | Frontend unit tests (Vitest): money, form validation, workflow state | 🟠 High-ish | Medium | Sonnet |
| FILE_05 | README cross-platform (Linux/macOS install) + fix Django 6 deprecation | 🟢 Low | Small | Haiku |

## Phase 2 — Nice-to-Have (future, founder-paced)

| File | Task | Effort |
|---|---|---|
| FILE_06 | a11y CI check (axe-core) on top RTL screens | Small |
| FILE_07 | OpenAPI/Swagger schema (drf-spectacular) for integration partners | Medium |
| FILE_08 | Architecture diagrams (mermaid/C4) in `architecture/` | Small |
| FILE_09 | Load/perf test at realistic multi-branch, multi-user volume | Medium |
| — | Celery Flower / task-monitoring UI; Storybook — evaluate if the operator panel + brand review make them redundant before building | — |

## Locked decisions
1. **Reference, don't duplicate** — smart-import UI, admin panel, AI cost, AI reliability stay in
   their own plans; this index just tracks that they're the audit's other "remaining" items.
2. **Static-analysis tools already exist** (`ruff`, `mypy` in `pyproject.toml`) — FILE_01 only wires
   them into the CI from `pre-handover-hardening/FILE_02`; `bandit` is the one net-new dev tool
   (security lint) — DECISIONS entry before adding.
3. **No new runtime deps.** Vitest, axe-core, drf-spectacular are dev/tooling — still ask before
   adding, per team rule 7.

## Change log
- **2026-07-18 — Created** from the QA audit Phase 1/2. Positioned in `EXECUTION_ORDER.md` as pos
  8-D (after handover; interleavable with the numbered roadmap once live).
- **2026-07-19 — Phase 1 (FILE_01–05) all done**, ahead of the "after handover" sequencing note —
  founder explicitly redirected a session onto B's backlog once browser-dependent B-scope work
  (brand-philosophy-review, twenty-harvest FILE_21) turned out not runnable in that session's
  harness (no screenshot/JS-eval tool). None of FILE_01–05 is customer-facing or risky
  pre-handover (CI lint, dependency lockfile, coverage baseline, JS unit tests, README/deprecation
  fix), so doing them early cost nothing. Full detail + baseline tables in `DECISIONS.md`. Phase 2
  (FILE_06–09, Nice-to-Have) remains founder-paced, not started.
