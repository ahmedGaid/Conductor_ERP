# FILE_01 — Enforce ruff + mypy + bandit in CI

## Finding
`ruff` and `mypy` are pinned in `requirements.txt` and configured in `pyproject.toml`, but NO gate
or CI invokes them (grep across `scripts/gates/*.py` = no matches). `bandit` (security lint) is
absent entirely. Type + security-lint drift accumulates invisibly.

## Tasks
- [ ] Add a `lint` job to `ci.yml` (from `pre-handover-hardening/FILE_02`): `ruff check .`,
      `mypy` (per `pyproject.toml` config), `bandit -r erp/`.
- [ ] Add `bandit` to dev requirements — DECISIONS entry first (net-new tool).
- [ ] Fix or explicitly baseline the current findings so the job starts green (don't merge a red
      gate; triage real issues, baseline accepted ones with a documented ignore).
- [ ] Make the job blocking on `pull_request`.

## Done when
CI `lint` job runs ruff+mypy+bandit and is green on `main`; a new type error or bandit high-severity
finding turns it red.

## How to test
- PR with a type error → mypy fails CI.
- PR with `eval(user_input)` → bandit fails CI.
