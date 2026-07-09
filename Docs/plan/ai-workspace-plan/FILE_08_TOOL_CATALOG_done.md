# SESSION 8 — Tool Catalog: the ERP's Read Surface
# Files: erp/assistant/tools.py, erp/*/contracts.py (additive helpers only where a tool needs one), erp/assistant/services/ask.py, erp/assistant/tests/test_tools.py (new)

---

## PROGRESS 2026-07-04 — Tasks A–D SHIPPED; Task E (query_data) still to do (user-approved split)

Per the session-economy split the file itself offers below, this session delivered the **hand-written
catalog (Tasks A–D)** only; the bounded `query_data` tool (**Task E**) is its own next session before
FILE_09. **Do NOT rename this file `_done` until Task E ships.**

Delivered (16 new read tools, 21 total): Sales (unchanged 4) · Customers `customer_profile`,
`find_customers` · Purchasing `open_purchase_orders`, `supplier_balances`, `purchase_summary` ·
Inventory `stock_on_hand`, `stock_movements`, `expiring_batches` · Accounting `trial_balance_summary`,
`income_statement_summary`, `vat_return_status`, `find_journal`, `account_balance` · Workflows
`workflow_instance_status` · Audit `document_history`. New scoped/gated contract helpers in
sales/purchasing/inventory/accounting contracts + `workflow.services.instance_status`; audit read is
direct ORM narrowed to `accessible_modules`. Router schema grew 6 args (status/supplier/warehouse/
days/entity_type/entity_id) + "pick the most specific" rule + module-grouped catalog. Frontend:
`AskCitation` union + `CitationLink` gained supplier/purchaseOrder/journal. Tests `test_tools.py`
(happy path + citation + a parametrized **refusal** per gated tool). GREEN: gate:all 00–13, assistant
70, tsc -b, parity 1535, gate03. (Note: `overdue_payables` from Task B is covered by
`supplier_balances` — not duplicated.)

**NEXT (fresh session):** Task E below — `query_data` + `erp/assistant/query_registry.py` + the
refusal tests, then rename `_done` and go to FILE_09.

---

## SCOPE DECISION 2026-07-03 (user-approved) — add a bounded structured-query tool

User wants the assistant to "read and analyze my data like ChatGPT reads the web" — ask anything,
not only the questions someone hand-built a tool for. Hand-written tools alone always leave gaps
(the live bug: "how many items do we have" had no tool → wrongly answered "outside your access").

**Approved approach: the hand-written catalog below (Tasks A–D) PLUS a bounded structured-query /
analytics tool (new Task E).** The query tool is a single typed tool the model fills in — pick a
whitelisted entity, filters, group-by, and an aggregate (count/sum/avg/min/max) — that the SERVER
validates, scopes (`scope_queryset` as the actor), and runs. It is **not** free-text-to-SQL
(DECISIONS.md still bans that): no raw SQL, no arbitrary fields, only a fixed grammar over a
registry of allowed entity+field combinations, RBAC + branch-scope + audit fully intact. This is
what turns "answers ~18 canned questions" into "answers most questions about the data." Do NOT
reopen the SQL ban — the structured grammar is the whole point.

If this session gets large, split it: Tasks A–D (catalog) first, Task E (query tool) can be its own
follow-up before FILE_09 — but both ship before the agent loop, because the loop composes them.

---

## Before You Start

1. Open `erp/assistant/tools.py` → read the whole file: the `Tool` dataclass (`name`,
   `description`, `args`, `run`, `cite`), the `_egp` formatter, the 5 existing tools
   (`_sales_summary`, `_top_customers`, `_overdue_receivables`, `_find_orders`, `_low_stock`), and
   the citation builders. **Every new tool follows this exact shape.**
2. Open `erp/sales/contracts.py` and `erp/inventory/contracts.py` → the scoped, actor-aware helper
   style tools wrap. New tools call contracts, never ORM directly from tools.py.
3. Open `erp/purchasing/contracts.py`, `erp/accounting/contracts.py` (find exact names via
   codegraph/grep), `erp/workflows/`, `erp/audit/models.py` → inventory what read helpers already
   exist before writing any new one.
4. Open `erp/assistant/services/ask.py` → the router prompt that lists tools; it must scale to
   ~20 tools without bloating (name + one-line description + args only).

"Do not write anything yet."

---

## Task A — Contract inventory, then gap list

For each module below, list existing contract helpers that already answer the question; only where
none exists, add ONE new helper to that module's `contracts.py` (same signature style: `(actor,
*, ...)`, scoped, returns plain dicts, minor units). Do not modify existing helpers.

## Task B — New tools (target catalog, ~18 total)

Add to `tools.py`, grouped with section comments matching the existing file's style:

**Purchasing** — `open_purchase_orders(status?, supplier?)`, `supplier_balances(limit)`,
`purchase_summary(period)`.
**Inventory** — `stock_on_hand(sku_or_query, warehouse?)`, `stock_movements(sku, limit)`,
`expiring_batches(days)`.
**Accounting** — `trial_balance_summary(period)`, `income_statement_summary(period)` (revenue,
expenses, net — reuse the dashboard's report contract), `vat_return_status(period)`,
`overdue_payables(limit)`, `find_journal(query|id)`, `account_balance(code_or_name)`.
**CRM** — `customer_profile(code_or_name)` (balance, recent orders, overdue), `find_customers(query)`.
**Workflows** — `workflow_instance_status(id_or_document)` — current step, waiting-on, history;
this answers "why did this workflow stop?".
**Audit** — `document_history(entity_type, entity_id, limit=10)` over `AuditEntry` (read-only ORM
here is acceptable — audit has no contracts layer; filter + order, never mutate). Answers "who
modified this document?".

Rules carried from the file header docstring (keep them true):
- every `run(actor, ...)` executes as the actor — RBAC/data-scope enforced by the contract
- money formatted via `_egp` server-side; models never invent numbers
- every tool gets a `cite` builder returning real click-through records (extend the citation
  `type` union as needed: `"supplier" | "journal" | "workflow"` … — mirror in
  `api/assistant.ts`'s `AskCitation` and the frontend `CitationLink` icon map)
- a tool receiving a permission error returns `{"error": "...calm human sentence..."}` — the model
  relays it honestly instead of hallucinating

## Task E — Bounded structured-query tool (the "ask anything" tool)

One new tool `query_data` — the model's escape hatch when no specific tool fits. NOT raw SQL: a
fixed grammar over an allow-list.

- **Registry** (`erp/assistant/query_registry.py`, new): a dict mapping each queryable entity
  (`item`, `sales_order`, `customer`, `supplier`, `journal`, …) → the module contract/queryset it
  reads, its filterable fields (name → type), its group-by-able fields, and which numeric fields may
  be aggregated. Only what is listed here is reachable. Reuse the RBAC module map — an entity a
  user's role can't see is refused with the same calm error as any other tool.
- **Tool args** (validated server-side, reject anything off-registry): `entity`, `filters`
  (list of `{field, op, value}`, ops from a fixed set `eq/gt/lt/gte/lte/contains/between`),
  `group_by` (0–2 fields), `aggregate` (`count | sum | avg | min | max`), `metric` (the numeric
  field for non-count aggregates), `limit`.
- **Execution**: build the queryset via the entity's contract, run it through `scope_queryset` as
  the actor (so branch/scope holds), apply validated filters + `.values(group_by).annotate(agg)`,
  format money via `_egp`, cap rows at `limit`. Never `eval`, never string-built SQL, never a field
  not in the registry.
- **Citations**: when the grouped result rows map to real records (customers, items…), reuse the
  existing citation builders; pure aggregates (a single count) cite nothing.
- **Router**: `query_data` is the fallback the router picks when no specific tool matches — update
  the router prompt so a plain "how many items do we have" routes here (`entity=item,
  aggregate=count`) instead of `tool=none`.

Tests (in `test_tools.py` or a sibling `test_query_tool.py`): a count, a group-by-with-sum, a
filter, an off-registry entity rejected, an off-registry field rejected, and a scoped-user test
proving branch-scope still filters the rows. This tool is the one that must be hardest to abuse —
test the refusals as carefully as the happy paths.

## Task C — Router scaling

In `services/ask.py`, the tool list in the router prompt is now generated from the catalog
(`name — description — args`), grouped by module. Add a final router rule: "If several tools could
help, pick the single most specific one" (multi-tool chaining arrives with the agent loop in
session 9 — do not build it here).

## Task D — Tests

`erp/assistant/tests/test_tools.py`: for each new tool — happy path with seeded data (borrow
factories/fixtures from that module's own tests), citation shape, and one scoped-user test proving
a user without the module permission gets the calm error, not data. Keep it table-driven so 18
tools stay readable.

---

## Smoke Test

- [ ] "Who changed sales order X?" → audit-backed answer with actor + timestamps
- [ ] "Why is workflow Y stuck?" → current step + who it waits on
- [ ] "What's our VAT position this month?" / "cash vs last month?" → accounting tools fire
- [ ] "Stock of SKU-123 in warehouse A?" → scoped inventory answer with item citation
- [ ] Limited user asks an accounting question → calm refusal, zero data leak
- [ ] Old suggestions (s1–s4) still route to the original 5 tools — no regressions
- [ ] `pytest erp/assistant` fully green; `npx tsc --noEmit` green (citation union)

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_09_AGENT_LOOP.md and continue
```
