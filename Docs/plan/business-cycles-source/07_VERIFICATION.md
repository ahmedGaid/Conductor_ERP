# Final Verification Checklist — Business Cycles Expansion

## Full verification suite

Add these Makefile targets (each maps to its golden rule; keep the numbering visible in output):

```makefile
verify-cycles: verify-c1-c3 verify-c4 verify-c5 verify-c6-c8 verify-e2e

verify-c1-c3:   ## C1–C3: quantities + chaining (O2C spine, cash)
	psql $(DB_URL) -v ON_ERROR_STOP=1 -f db/tests/test_o2c_spine.sql
	psql $(DB_URL) -v ON_ERROR_STOP=1 -f db/tests/test_o2c_cash.sql

verify-c4:      ## C4: ETA lifecycle
	psql $(DB_URL) -v ON_ERROR_STOP=1 -f db/tests/test_eta_lifecycle.sql

verify-c5:      ## C5: 3-way match
	psql $(DB_URL) -v ON_ERROR_STOP=1 -f db/tests/test_p2p.sql

verify-c6-c8:   ## C6–C8: periods, balanced journals, append-only
	psql $(DB_URL) -v ON_ERROR_STOP=1 -f db/tests/test_r2r.sql

verify-e2e:     ## Full O2C + P2P + close smoke test
	psql $(DB_URL) -v ON_ERROR_STOP=1 -f db/tests/test_full_cycle.sql
```

Then run everything:

```bash
make verify          # original slice invariants — must be green, untouched
make verify-cycles   # all cycle invariants C1–C8
```

Additional grep checks — ALL must return nothing:

```bash
# No direct writes to document tables from the app layer (G-WRITE-PATH):
grep -rn "INSERT INTO \(sales_order\|delivery\|ar_invoice\|customer_receipt\|purchase_order\|goods_receipt\|supplier_invoice\|supplier_payment\|journal_event\)" src/ --include='*.ts'

# No state-conditional editability in the UI (G-MUTABILITY):
grep -rn "state ===\|status ===" src/ --include='*.tsx' | grep -i "disabled\|readonly\|editable"

# No stored open/derived quantities (C1):
psql $(DB_URL) -c "\d+ sales_order_line" | grep -i "qty_open" && echo "FAIL: stored derived qty" || true

# No hardcoded tolerances or tax rates in procedures (C5):
grep -rn "0\.02\|tolerance :=\|tax_rate :=" db/migrations/ db/procs/ || true

# ETA feature flag defaults to false:
psql $(DB_URL) -c "SELECT column_default FROM information_schema.columns WHERE table_name='tenant_settings' AND column_name='eta_enabled'" | grep -q false
```

## Summary of what was created

- Documents: delivery, ar_invoice, customer_receipt, purchase_order, goods_receipt, supplier_invoice, supplier_payment (+ line tables, + receipt/payment applications)
- Compliance: eta_submission (immutable), ETA state machine on ar_invoice
- Matching: match_tolerance, match_exception, sp_match_supplier_invoice
- Accounting: accounting_period, account, posting_rule, journal_event (append-only, group-balanced), trial balance view
- Chain procedures: SO→delivery→invoice; PO→receipt→supplier invoice; receipts/payments application with reversal-only unapply
- field_mutability + RBAC seeds for every new document type; workspaces cloned from the Sales Order skeleton

## Modified existing files (should be this list and NOTHING more)

- `sales_order_line`: additive quantity columns + guard trigger (Phase 1)
- Posting procedures from Phases 1–4: additive period-guard + journal-emission calls (Phase 5 only)
- `Makefile`: new verify targets
- Workspace routing/registry: new document routes registered at the end, existing routes untouched

If your diff shows anything outside this list, revert it and explain why it seemed necessary.

## Update the skill

Open `/mnt/skills/user/ag-code-instructor/SKILL.md` and append to the Learned patterns section:

```
- conductor-cycles (2026): Conductor extends by CYCLES not modules. New document types always ship
  as: table pair (header/lines) + chain columns (source_doc_type/id/line_id) + C1 quantity columns
  + field_mutability seeds + RBAC scopes + event-log enrollment + workspace clone — in ONE phase.
  Posting procedures are the only place quantities on source lines change. Period guard + journal
  emission live inside posting procedures, wired in a single dedicated phase after all posting
  points exist. Tolerances/tax/periods are always data tables, never constants. Reversal-only
  corrections everywhere (no reopen, no delete). [Add any gotchas actually discovered during the run.]
```

## Done

Report back: which verifications passed, which document types are live, and the trial balance of
the e2e test run.
