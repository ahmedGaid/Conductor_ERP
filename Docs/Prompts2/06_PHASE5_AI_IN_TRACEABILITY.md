# Phase 5 — Intelligence, Inside Trust
# LOW RISK if and only if AI cannot commit. That is the whole point.

Honor: Rule 5 (AI suggests, human commits, timeline records), Rule 4 (events),
Rule 2 (suggestions are permission-shaped too).

## The single hard rule
AI may **propose**. AI may **never** post, reverse, change a price, or move stock
on its own. Every AI effect flows: `suggestion → human accept → normal write path
→ event_log(source='ai', accepted_by=<human>)`. There is no other channel.

## What you will do
1. A suggestion producer that writes to `ai_suggestion` (PROPOSED) — read-only.
2. An accept endpoint that applies the change via the SAME guarded write path.
3. UI chips that surface suggestions; accepting requires a human click.
4. Timeline integration so accepted suggestions show AI + approver.

---

## Step 1 — Produce suggestions (read-only; never mutates business data)
```ts
// api/src/ai/suggest.ts — examples kept SAFE (informational), per the owner's spec
// "Customer usually receives 10%." / "Warehouse B has more stock." / "Demand rising → suggest PO."
async function suggestForSO(docId: number): Promise<Suggestion[]> {
  // read-only queries: price history, stock by warehouse, demand trend
  // returns proposals; writes ONLY to ai_suggestion(status='PROPOSED')
}
```
```sql
insert into ai_suggestion(entity,entity_id,kind,payload,status)
values('document', :docId, 'DISCOUNT',
       jsonb_build_object('field','unit_price_amount','line_id',:lineId,'proposed',95,'reason','usual 10%'),
       'PROPOSED');
```

## Step 2 — Accept = the normal guarded write (no AI shortcut)
```ts
// POST /suggestions/:id/accept  (human-authenticated)
async function accept(suggestionId: number, user: User) {
  const s = await getSuggestion(suggestionId);
  // set transaction context so the event records BOTH ai origin and human approver:
  await db.query(`SET LOCAL conductor.user_id = $1`, [user.id]);
  await db.query(`SET LOCAL conductor.source  = 'ai'`);   // marks origin
  // apply via the EXACT same path a human edit uses — all guards still run:
  await patchSalesOrderField(s.entity_id, s.payload.field, s.payload.proposed, user);
  await db.query(
    `update ai_suggestion set status='ACCEPTED', accepted_by=$1, accepted_at=now() where suggestion_id=$2`,
    [user.id, suggestionId]);
  // The event_log row written by the trigger now has source='ai' + actor=user.
}
```
Because it reuses `patchSalesOrderField`, a suggestion to edit a **posted**
financial field is rejected exactly like a human attempt — the AI gets no
privilege.

## Step 3 — UI: chips, never auto-apply
```tsx
// Suggestions appear as dismissable chips near the relevant field/line.
// "Customer usually receives 10% — Apply?"  [Apply] [Dismiss]
// [Apply] calls /suggestions/:id/accept. Nothing happens without that click.
function SuggestionChip({ s }: { s: Suggestion }) {
  return <div className="chip">
    <span>{s.payload.reason}</span>
    <button onClick={() => accept(s.id)}>Apply</button>
    <button onClick={() => dismiss(s.id)}>Dismiss</button>
  </div>;
}
```

## Step 4 — Timeline shows the full story
Accepted suggestion → timeline row reads:
`14:02 · price 100 → 95 · suggested by AI · accepted by Ahmed`
So "who/why" stays answerable, and AI lives **inside** traceability (Rule 5/4),
not beside it.

## Verification for Phase 5
```bash
# 1. A suggestion to edit a POSTED financial field is REJECTED on accept (422), like a human edit.
# 2. No business row ever changes from status PROPOSED alone (no human click) — assert no event with
#    source='ai' exists unless a corresponding ai_suggestion.status='ACCEPTED' with accepted_by is set.
psql "$DB_URL" -tAc "
 select count(*) from event_log e
 where e.source='ai'
   and not exists (select 1 from ai_suggestion s
                   where s.status='ACCEPTED' and s.accepted_by is not null
                     and s.entity=e.entity and s.entity_id=e.entity_id);"   # expect 0
# 3. UI: chip never mutates without [Apply].
```

## What you just built
A colleague, not an autopilot. AI broadens what users *see*; humans still decide,
and the timeline records that an AI proposed it and a named person accepted it.

## Next file: 07_VERIFICATION.md
