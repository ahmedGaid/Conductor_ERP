# FILE_03 — Backend coverage reporting

## Finding
1,415 backend tests exist but there is no coverage config (`.coveragerc`, `[tool.coverage]`, or
`coverage`/`pytest-cov` in requirements). "High coverage" is currently unverifiable — only test
COUNT is known.

## Tasks
- [ ] Add `pytest-cov` (dev req; DECISIONS entry) + `[tool.coverage]` config in `pyproject.toml`.
- [ ] Run `pytest --cov=erp --cov-report=term-missing`; record the baseline % per app in a short
      note.
- [ ] Surface coverage in the CI backend job output (not necessarily a blocking threshold at
      first — measure before gating).
- [ ] Optionally set a non-regression floor once the baseline is known.

## Done when
`pytest --cov` produces a per-module coverage report; baseline recorded; CI prints coverage.

## How to test
- `pytest --cov=erp` → coverage summary appears with per-file missing lines.
