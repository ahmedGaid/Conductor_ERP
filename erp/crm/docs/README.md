# CRM module

Customer relationship management (Stage 5f). Customer priority #5 — the last priority module. The
relationship side of the ERP: it owns the funnel and post-sale support, and bridges into Sales.

## Pieces
- **Leads** — top of funnel: capture → `contacted`/`qualified`/`unqualified` → **convert** (creates a
  pipeline opportunity once; a converted lead can't convert again, `CRM-002`).
- **Opportunities (pipeline)** — `qualifying → proposal → negotiation → won | lost`, with line items
  (SKU + qty + price), an `amount_minor` and a `weighted_minor` (× probability). **Winning** can hand
  the deal to Sales.
- **Activities** — calls/emails/meetings/tasks/notes logged against any record (lead/opportunity/
  ticket) by `related_type` + `related_ref`; mark done.
- **Support tickets** — priority-driven **SLA**: due time computed at open (urgent 4h, high 8h,
  medium 24h, low 72h). A still-open ticket past its due time is **breached** (`Ticket.is_breached`).
  `open → in_progress → resolved → closed`.

## Cross-module: win → Sales order
`win_opportunity(opp, create_sales_order=True)` calls **`erp.sales.contracts.place_order`** with the
customer **code** + line inputs — strings only, no sales ORM crosses the boundary (enforced by
gate09). It creates a draft sales order and records its number on the opportunity. If the customer
code is unknown in Sales it raises `CRM-003`; with no lines, `CRM-004`. Pass
`create_sales_order=False` to win a non-order deal without touching Sales.

## Invariants (proven by `tests/`)
1. Lead convert creates an open opportunity and stamps the lead `converted` (once only, `CRM-002`).
2. Winning with a valid customer + lines creates a **draft sales order via the contract** whose
   subtotal equals the opportunity amount; the opportunity records its number.
3. Winning into an unknown customer (`CRM-003`) or with no lines (`CRM-004`) is rejected.
4. Ticket SLA: due time matches priority; an overdue open ticket is breached, a resolved one is not.
5. Every transition is atomic and guarded (`CRM-001`).

## Next slices
Campaigns + lead scoring, opportunity products synced to quotations, ticket escalation rules +
notifications, activity calendar, and an account/contact model unifying leads and customers.
