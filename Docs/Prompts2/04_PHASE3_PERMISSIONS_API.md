# Phase 3 — Permissions & API
# MEDIUM RISK — this is where data leaks happen. Field-level security is the test.

Honor: Rule 2 above all (context respects permission), Rule 4 (set actor for events).

## What you will do
1. Set transaction context (`user_id`, `source`) so events + scope work.
2. Row-level scope: every read filters by `data_scope`.
3. Field-level shaping: forbidden fields are **deleted from the payload**, not flagged.
4. Action gating: the actions list is computed from permission **AND** state.
5. The Sales Order API contracts (header, lines, drawer, actions).

> API is a **thin** layer. It must not contain posting/tax/FX logic — it calls the
> Phase 2 procedures. Its only real job is auth, scope, shaping, and transport.

---

## Step 1 — Transaction context (every request)
At the start of each DB transaction the API runs:
```sql
SET LOCAL conductor.user_id = $1;
SET LOCAL conductor.source  = 'human';   -- 'ai' only via the suggestion-accept path
```
This drives the event trigger (Phase 2) and scope checks below.

## Step 2 — Row-level scope (reads)
Every list/read query joins data_scope. Reference helper:
```sql
create or replace function user_can_see_org(p_user bigint, p_org bigint)
returns boolean language sql stable as $$
  select exists(select 1 from data_scope where user_id=p_user and org_id=p_org);
$$;
```
API rule: **no document/master read may omit the org-scope filter.** A request
for an out-of-scope `document_id` returns 404 (not 403 — don't confirm existence).

## Step 3 — Field-level shaping (the leak surface)
This is the single most-tested behaviour. Build ONE shaping function the whole API
funnels through. Pseudocode (TypeScript / NestJS reference):
```ts
// api/src/security/shape.ts
type Grant = { entity: string; field: string; canView: boolean; canEdit: boolean };

export function shape(entity: string, row: Record<string, any>, grants: Grant[]) {
  const sensitive = grants.filter(g => g.entity === entity && !g.canView).map(g => g.field);
  const out = { ...row };
  for (const f of sensitive) delete out[f];      // ABSENT, not nulled, not hidden
  return out;
}
// Sensitive defaults if no grant row exists for a role: DENY (can_view=false).
```
Rules:
- Default-deny: a field with no grant for the user's role is **removed**.
- `margin`, `std_cost_amount`, `credit_limit_amount` are sensitive by default.
- Writes: before any update, check `field_grant.can_edit` AND
  `assert_field_mutable()` (Phase 2). Either failing → reject the write.

```sql
-- helper the API calls before writing a field
create or replace function user_can_edit_field(
  p_user bigint, p_entity text, p_field text
) returns boolean language sql stable as $$
  select coalesce(bool_or(fg.can_edit), false)
  from user_role ur join field_grant fg on fg.role_id=ur.role_id
  where ur.user_id=p_user and fg.entity=p_entity and fg.field=p_field;
$$;
```

## Step 4 — Action gating (permission AND state)
The workspace asks the API "what can I do?" The server — never the client — decides:
```ts
// returns only allowed actions for THIS user on THIS document
function availableActions(doc, perms: Set<string>): string[] {
  const a: string[] = [];
  if (doc.status === 'DRAFT') {
    a.push('edit');
    if (perms.has('doc.post')) a.push('post');
    a.push('delete');
  }
  if (doc.status === 'POSTED') {
    a.push('print', 'share', 'pdf', 'duplicate');
    if (perms.has('doc.reverse')) a.push('reverse');
    if (perms.has('doc.amend'))   a.push('amend');
  }
  return a;   // client renders ONLY these; it cannot invent 'post'
}
```
Invariant: the client never decides permissions; it renders the server's list.

## Step 5 — Sales Order API contracts
Implement these endpoints. All responses pass through `shape()`.
```
GET  /so/:id            -> { header, lines, totals, workflow, actions, fxContext }
                           header/lines already field-shaped; totals from engine
POST /so                -> create DRAFT (returns shaped header)
PATCH /so/:id           -> edit DRAFT field(s): per-field check
                           user_can_edit_field + assert_field_mutable, else 422
POST /so/:id/post       -> calls post_document(); returns posted header + actions
POST /so/:id/reverse    -> calls reverse_document(); returns the PAIR (orig+reversal)
GET  /so/:id/timeline   -> event_log rows for this doc, newest first (Rule 4 surface)
GET  /so/:id/drawer/customer  -> party panel, field-shaped (credit hidden if no grant)
GET  /so/:id/drawer/item/:itemId -> item panel (cost/margin only if granted)
GET  /so/compare?ids=1,2,3       -> N shaped headers+totals for SPLIT view (Principle 6)
```
Response envelope (every endpoint):
```json
{ "data": { ... }, "actions": ["..."], "meta": { "currency":"EGP", "fxFrozen": true } }
```

## Verification for Phase 3
```bash
# Field leak test — THE important one:
# As SALES_CLERK (no view.margin grant) request a posted SO; assert payload has NO 'margin','std_cost_amount'
curl -s -H "X-User: sales_clerk" $API/so/1 | jq 'paths | select(.[-1]=="margin")' # expect empty
# Cross-org: clerk scoped to org 1 requests org-2 doc -> 404
curl -s -o /dev/null -w "%{http_code}" -H "X-User: sales_clerk" $API/so/<org2_doc>  # expect 404
# Action gating: clerk without doc.post does NOT receive 'post'
curl -s -H "X-User: sales_clerk" $API/so/<draft> | jq '.actions | index("post")'   # expect null
# Write guard: clerk patch of unit_price on POSTED doc -> 422
curl -s -o /dev/null -w "%{http_code}" -X PATCH -d '{"unit_price_amount":5}' $API/so/<posted> # expect 422
```
All four must pass. The field-leak test is non-negotiable.

## What you just built
A server that *shapes* every payload to the user's grants, decides actions itself,
and refuses illegal writes — so the beautiful UI in Phase 5 literally cannot
display or send something the user isn't allowed to.

## Next file: 05_PHASE4_WORKSPACE_UI.md
