# SESSION 20 — AI Usage & Cost Visibility
# Files: erp/assistant/api (read endpoint over gateway data), apps/web settings→AI page (extend or new), i18n locales

Twenty reference: workspace AI usage stats + metered AI billing. Ours: the reliability gateway
ALREADY tracks tokens/cost/budgets — this session makes the owner able to SEE it. Trust +
no bill shock; numbers click-verifiable (mechanic 4). No chart ships without the decision it
informs (STRATEGY §5): every number here answers "should I raise/lower the budget?"

---

## Before You Start

1. Open the reliability-gateway budget/usage storage (`erp/assistant/` — token/cost budgets +
   traces from ai-reliability Phase 1–2) → the exact fields available. This session adds ZERO
   new tracking.
2. Open the existing assistant/AI settings surface in apps/web → extend, don't fork.
3. Open `lib/money.ts` → EGP formatting for cost (minor units on the wire).

"Do not write anything yet."

---

## Task A — Read endpoint

`/api/assistant/usage/?month=` (admin role): totals (requests, tokens in/out, cost minor units,
cache-hit share, degraded-mode minutes), per-provider split, per-user table, budget vs consumed.
Straight aggregation over gateway records — any number the endpoint can't derive from stored
data is NOT shown (no estimates presented as facts).

## Task B — The page

Settings → AI: budget bar (consumed/limit, word+number, color only paired with the word),
month picker, per-user table (user, requests, tokens, cost), provider split line, cache-hit
line ("وفّر التخزين المؤقت …"). Each aggregate links to its trace list (existing ops/traces
view) — click-verifiable. Empty/no-key state: designed, explains AI is off and the app is fully
functional (calm, not apologetic).

## Task C — Tests

Aggregations match seeded gateway records; admin-only; minor-units integrity end to end.

---

## Smoke Test

- [ ] Run 3 assistant queries → page shows them, cost formatted EGP, numbers match trace count
- [ ] Click a total → lands on the matching traces
- [ ] No-API-key environment → designed off-state, no errors
- [ ] `pytest erp/assistant` green; parity + tsc + gate03 green; brand checklist passed

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_21_ACCEPTANCE.md in a FRESH session.
```
