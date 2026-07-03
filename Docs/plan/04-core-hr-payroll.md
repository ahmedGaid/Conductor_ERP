# Session 04 — HR + payroll (Egypt-specific)

**Goal:** employee records + monthly payroll that posts to the GL, correct for **Egyptian** social
insurance and income-tax brackets. This is a compliance moat — getting Egyptian payroll right is
hard and sticky. Recall `conductor-brand` + `erp-frontend`. Branch `feat/module-hr`.

> Egyptian statutory rules change; put the **rates/brackets in configurable, dated tables**, never
> hardcoded. Verify current rates with the user or an authoritative source before shipping numbers —
> the *engine* is the deliverable here, the *rates* are seed data the user confirms.

## Scope (v1)
- **Employees:** personal + job data, salary structure (basic + allowances), branch/department/team
  (reuse the org primitives already in `AuditedModel`).
- **Payroll run:** monthly, per branch. Gross → deductions (social insurance employee share, income
  tax by bracket) → net. Employer costs (social insurance employer share) tracked separately.
- **GL posting:** payroll run posts Dr salary expense / Cr net-payable + tax-payable + insurance-
  payable. Reuses the accounting service.
- **Payslip:** per-employee PDF (reuse the zero-dep client print-to-PDF pattern from the invoice doc).

## Tasks
1. New app `erp/hr/`. Models: `Employee`, `SalaryComponent`, `PayrollRun`, `Payslip`,
   `PayrollLine`. Dated config: `SocialInsuranceRate`, `IncomeTaxBracket` (effective_from/to) — same
   dated-resolver shape as the pricing engine's effective-date resolver (reuse that pattern).
2. **Payroll engine** (`services/run.py`): pure function `compute_payslip(employee, period, config)`
   → gross, itemized deductions, net. Deterministic, fully unit-tested against hand-worked examples.
3. **Bracket resolver:** progressive income tax (annualized then de-annualized per the Egyptian
   method) — implement carefully, test each bracket boundary.
4. **Run lifecycle:** draft → review → approve (RBAC + approval limit) → post to GL → locked.
   Idempotent posting (no double-pay on retry).
5. **UI:** Employees list/detail; Payroll run wizard (select period+branch → preview lines →
   approve → post); payslip viewer. Arabic-first, designed states, blame-free errors.
6. **RBAC:** new `hr.*` permission codes; payroll is scope-sensitive (a branch manager sees only
   their branch — Session 00 scoping applies).

## Done bar
- A worked example (known salary → known SI + tax → known net) matches to the piaster.
- Payroll run posts a balanced GL journal; re-running the same period is refused/idempotent.
- `gate:all` GREEN; parity + `tsc -b` + `gate03` GREEN.
- DECISIONS.md "HR 2026-07": rates are dated config (not code); source + as-of date noted.
