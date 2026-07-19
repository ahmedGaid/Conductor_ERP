# FILE_03 — Backend coverage reporting

## Finding
1,415 backend tests exist but there is no coverage config (`.coveragerc`, `[tool.coverage]`, or
`coverage`/`pytest-cov` in requirements). "High coverage" is currently unverifiable — only test
COUNT is known.

## Tasks
- [x] Add `pytest-cov` (dev req; DECISIONS entry) + `[tool.coverage]` config in `pyproject.toml`.
- [x] Run `pytest --cov=erp --cov-report=term-missing`; record the baseline % per app in a short
      note.
- [x] Surface coverage in the CI backend job output (not necessarily a blocking threshold at
      first — measure before gating).
- [x] Optionally set a non-regression floor once the baseline is known.

## Done when
`pytest --cov` produces a per-module coverage report; baseline recorded; CI prints coverage.

## How to test
- `pytest --cov=erp` → coverage summary appears with per-file missing lines.

## Closed 2026-07-19 (A) — baseline table in DECISIONS.md
1427 tests, 89% overall (18043 statements, 1983 missed), ~6 min locally. `fail_under = 84` set in
`pyproject.toml` (5 points below baseline, same margin pattern as gate15). CI `backend` job's
pytest step now runs `--cov=erp --cov-report=term-missing`.
