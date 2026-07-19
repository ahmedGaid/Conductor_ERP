# FILE_01 — Enforce ruff + mypy + bandit in CI

## Finding
`ruff` and `mypy` are pinned in `requirements.txt` and configured in `pyproject.toml`, but NO gate
or CI invokes them (grep across `scripts/gates/*.py` = no matches). `bandit` (security lint) is
absent entirely. Type + security-lint drift accumulates invisibly.

## Tasks
- [x] Add a `lint` job to `ci.yml` (from `pre-handover-hardening/FILE_02`): `ruff check .`,
      `mypy` (per `pyproject.toml` config), `bandit -r erp/`.
- [x] Add `bandit` to dev requirements — DECISIONS entry first (net-new tool).
- [x] Fix or explicitly baseline the current findings so the job starts green (don't merge a red
      gate; triage real issues, baseline accepted ones with a documented ignore).
- [x] Make the job blocking on `pull_request`.

## Done when
CI `lint` job runs ruff+mypy+bandit and is green on `main`; a new type error or bandit high-severity
finding turns it red.

## How to test
- PR with a type error → mypy fails CI.
- PR with `eval(user_input)` → bandit fails CI.

## Closed 2026-07-19 (A) — full triage in DECISIONS.md
`ruff check .`, `mypy erp config`, `bandit -r erp/ -c pyproject.toml` all exit 0 locally. Baseline
approach (not a fix-everything pass) — see DECISIONS.md "post-handover-v1_1 FILE_01" entry for the
per-tool triage rationale (~1679 ruff findings, 202 mypy errors, 3494 bandit findings reviewed by
class/sample, not individually).
