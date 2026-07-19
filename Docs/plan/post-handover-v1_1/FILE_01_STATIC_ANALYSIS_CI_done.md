# FILE_01 — Enforce ruff + mypy + bandit in CI

## Finding
`ruff` and `mypy` are pinned in `requirements.txt` and configured in `pyproject.toml`, but NO gate
or CI invokes them (grep across `scripts/gates/*.py` = no matches). `bandit` (security lint) is
absent entirely. Type + security-lint drift accumulates invisibly.

## Tasks
- [x] Add a `lint` job to `ci.yml` (from `pre-handover-hardening/FILE_02`): `ruff check .`,
      `mypy` (per `pyproject.toml` config), `bandit -r erp/`.
- [x] Add `bandit` to dev requirements — DECISIONS entry first (net-new tool). Founder approved
      this session (asked directly); see DECISIONS.md 2026-07-19 entry.
- [x] Fix or explicitly baseline the current findings so the job starts green (don't merge a red
      gate; triage real issues, baseline accepted ones with a documented ignore). ruff: 190
      auto-fixed + 75 hand-fixed (real bugs/style) + E501 (1401, pre-existing) baselined. mypy: 50
      modules baselined (union of two flaky cold-run file sets — see DECISIONS.md), verified clean
      on 2 independent cold-cache runs. bandit: 4 findings, all false positives, `# nosec`'d with
      inline reasoning.
- [x] Make the job blocking on `pull_request` (top-level `on:` in `ci.yml` covers all jobs).

## Done when
CI `lint` job runs ruff+mypy+bandit and is green on `main`; a new type error or bandit high-severity
finding turns it red. **Done 2026-07-19 (Agent B, feat/b-prehandover):** `.github/workflows/ci.yml`
has a `lint` job (ruff, mypy, `bandit -r erp/ -ll`); verified green locally (ruff `All checks
passed!`, mypy `Success: no issues found in 657 source files` ×2 independent cold-cache runs,
bandit exit 0 with `-ll`). Full `pytest` (1415 passed) and full local gate harness (00–17, all
PASSED — log saved to `Docs/plan/delivery-readiness/gate-runs/gate-all-2026-07-19-post-handover-
file01.log`) confirm the lint fixes introduced no regressions. Not yet exercised on an actual GitHub
Actions run (no PR opened this session) — local verification only.

## How to test
- PR with a type error → mypy fails CI.
- PR with `eval(user_input)` → bandit fails CI.
- Locally: `ruff check .`, `mypy .`, `bandit -r erp/ -ll` — all exit 0 from repo root
  (`.venv\Scripts\python.exe -m <tool>` on this machine).
