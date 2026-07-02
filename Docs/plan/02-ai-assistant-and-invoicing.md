# Session 02 — AI assistant + AI invoicing (the headline)

**Goal:** embed a Claude-powered assistant that (a) turns a photo/PDF/email of an invoice into a
posted, ETA-ready document with a human confirm step, and (b) answers natural-language questions
over the user's *scoped* data. This is the "Linear of ERP" wedge. Depends on **Session 00** (the AI
must only ever read scope-filtered data). Recall `conductor-brand` + `erp-frontend`.

> This is 2–3 sessions of real work. Split at the `---` markers if needed. Read the `claude-api`
> skill before writing any Anthropic call. Use the latest model id (`claude-*`) per that skill; put
> the key in env (`ANTHROPIC_API_KEY`), never in code. For customer-hosted installs, the AI layer
> must be **optional and toggleable** (an install with no key still runs — degrade gracefully).

## Architecture (decide + write to DECISIONS.md first)
- New Django app `erp/assistant/`. It is a **thin orchestration layer**: it never touches other
  modules' ORM directly — it calls the same **service functions** the API uses, so RBAC + scope +
  audit are automatically enforced. The AI is just another actor with the caller's permissions.
- **Tool-use, not free-text-to-SQL.** Define a fixed set of typed tools the model may call
  (`search_customers`, `get_item_stock`, `draft_sales_order`, `extract_invoice_fields`, ...). Each
  tool = one existing service call, executed **as the current user** (pass `actor=request.user`),
  so scope/limits/audit hold. No raw SQL, no arbitrary ORM.
- **Human-in-the-loop for writes.** The model may *draft* (return a structured proposal); a write
  only happens when the user confirms in the UI. Never auto-post money.
- Cost control: token budget per request, per-tenant monthly cap (ties into Session 07 billing).

---

## Part 1 — Document → draft invoice (the magic demo)
1. Endpoint `POST /assistant/extract-document` (multipart): accepts image/PDF of a supplier invoice
   or receipt. Reuse the Session 00 upload limits.
2. Send to Claude with a **strict JSON schema** (tool/`response_format`): supplier name, tax id,
   date, currency, line items (desc, qty, unit price minor), subtotal, VAT, total. Arabic + English
   OCR — the model reads both; test with real Egyptian supplier invoices.
3. Map extracted fields to a **draft** purchase invoice / bill via the purchasing service (draft
   state, nothing posted). Fuzzy-match supplier + items to existing records; surface unmatched ones
   for the user to link or create.
4. UI: an `ActionReceiptCard`-style review surface (you already have the receipt engine on
   `feat/action-feedback-receipts`) showing extracted vs matched, with inline-edit on every field,
   confidence hints, and one **Confirm & post** action. Designed empty/low-confidence states.
5. On confirm → the normal purchasing post path → which already feeds VAT + (after Session 03) COGS.
   (Actual submission to ETA is Session 09 — this session produces the correct posted document;
   "ETA-ready" means the compliance record exists, not that it was transmitted.)

**Acceptance:** photo of a real supplier invoice → reviewed draft in < 10s → posted bill with correct
VAT and a linked audit entry. Wrong/blurry input → designed "couldn't read this, here's what I got"
state, never a 500.

---

## Part 2 — Natural-language assistant over scoped data
1. Endpoint `POST /assistant/ask` (streaming). System prompt states: Arabic-first, uses the
   canonical lexicon (Identity System §6), answers only from tool results, never invents numbers.
2. Register read tools (all scope-enforced): `sales_summary`, `inventory_low_stock`,
   `overdue_receivables`, `top_customers`, `find_document`. Each returns structured data the model
   summarizes.
3. Register draft-write tools that return proposals only: `draft_sales_order`, `draft_stock_transfer`
   — rendered as a confirm card, never executed silently.
4. UI: a calm command-bar-anchored panel (you have a command palette). Streaming answer, cited to the
   records it used (click-through via existing `EntityLink`). Reduced-motion honored.
5. Guardrails: refuse actions outside the user's permissions with a blame-free message; log every
   tool call to audit with the correlation id.

**Acceptance:** "كم مبيعات فرع القاهرة هذا الشهر؟" returns the correct scoped number with a link to
the orders; a Salesperson asking for another branch's data is politely refused (scope holds).

---

## Part 3 — Safety, cost, offline
1. Prompt-injection defense: extracted document text is **data, not instructions** — never feed it
   into the system prompt; keep it in a user-role content block; tools validate their own inputs.
2. Per-request token cap + per-tenant monthly cap; when exceeded → graceful "AI limit reached" state.
3. Feature flag `ASSISTANT_ENABLED` (off if no `ANTHROPIC_API_KEY`). All AI UI hidden when off.
4. `en.json` + `ar.json` parity for every new string (assistant is a first-class Arabic surface).

## Done bar
- `gate:all` GREEN; parity clean; `tsc -b` clean; `gate03` GREEN.
- Extraction + ask endpoints have tests using a **mocked** Anthropic client (no live calls in gates).
- DECISIONS.md "AI 2026-07": tool-use + human-in-the-loop + scope-as-actor recorded as the standing
  pattern; free-text-to-SQL explicitly rejected.
