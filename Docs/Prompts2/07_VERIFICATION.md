# Final Verification — Prove the Golden Rules Hold
# Run the whole suite. Every check maps to a numbered golden rule.

## The invariant suite (tests/invariants/smoke.sql + curl checks)
Put the SQL checks in `tests/invariants/smoke.sql` so `make verify` runs them
every time. A failing invariant = a broken product, not a failing test to skip.

### Rule 1 — Money is typed; FX frozen
```sql
-- no line where net+tax <> gross
select 'R1.tax_balance' as check, count(*) as fails
  from document_line where round(line_net+line_tax,4) <> line_gross;        -- 0
-- every posted doc has a frozen fx_rate
select 'R1.fx_frozen', count(*) from document where status='POSTED' and fx_rate is null; -- 0
-- base totals consistent with frozen rate (allow 0.01 rounding)
select 'R1.base_consistent', count(*) from document
 where status='POSTED' and abs(base_gross_amount - round(gross_amount*fx_rate,4))>0.01; -- 0
```

### Rule 2 — Permission (run via API)
```bash
# field leak: clerk payload has no margin/cost
test -z "$(curl -s -H 'X-User: sales_clerk' $API/so/1 | jq -r '..|.margin? // empty')" && echo R2.no_margin_OK
# cross-org: out-of-scope doc -> 404
[ "$(curl -s -o /dev/null -w '%{http_code}' -H 'X-User: sales_clerk' $API/so/$OUT_OF_SCOPE)" = 404 ] && echo R2.scope_OK
```

### Rule 3 — State machine + matrix
```sql
-- posted financials immutable (this block must NOT change any row)
do $$ begin
  begin update document set net_amount=net_amount+1 where status='POSTED';
        raise exception 'R3.FAIL posted edited';
  exception when others then raise notice 'R3.posted_immutable_OK'; end;
end $$;
-- reverse creates a linked successor with opposite sign
select 'R3.reversal_pair', count(*) from document r
 join document o on o.document_id = r.reverses_document_id
 where r.gross_amount <> -o.gross_amount;                                    -- 0
```

### Rule 4 — Total traceability
```sql
-- every posted doc has a POST event
select 'R4.post_logged', count(*) from document d
 where d.status in('POSTED','REVERSED')
   and not exists(select 1 from event_log e where e.entity='document'
                  and e.entity_id=d.document_id and e.action='POST');       -- 0
-- gl_entry is append-only (must RAISE)
do $$ begin begin delete from gl_entry where false; exception when others then null; end;
  begin update gl_entry set debit=debit where false; raise notice 'R4.gl_guard_present'; 
  exception when others then raise notice 'R4.gl_immutable_OK'; end; end $$;
```

### Rule 5 — AI cannot commit
```sql
select 'R5.no_orphan_ai', count(*) from event_log e
 where e.source='ai' and not exists(
   select 1 from ai_suggestion s where s.status='ACCEPTED'
     and s.accepted_by is not null and s.entity=e.entity and s.entity_id=e.entity_id); -- 0
```

## Full run
```bash
make verify            # migrate + seed + invariant-smoke
cd api && npm test && cd ../web && npm test
# then the curl checks above against a running API
```
ALL must pass. If any fails, do not declare done — open a HOTFIX file fixing only
the failing step.

## Summary of what this slice delivers
```
conductor/
  db/migrations/   001 reference, 002 tax, 003 masters, 004 document, 005 gl, 006 rbac+events
  db/seed/         currency/tax, field_mutability(SO), roles/grants
  db/             functions: resolve_tax_code, compute_document_totals, post_document,
                  reverse_document, amend_document, assert_field_mutable,
                  user_can_edit_field, + triggers (gl_immutable, doc_posted_guard, log_event)
  api/            scope + shape() + action gating + SO endpoints + suggestion accept
  web/            DocumentWorkspace, single Drawer, CompareView, ActionBar, Timeline, SuggestionChip
  tests/invariants/smoke.sql   the 5-rule proof suite
```
Modules intentionally NOT built yet (next instruction sets): Purchase, Invoice,
Manufacturing (graph skeleton), bulk lanes (Principle 11), e-invoice/ETA export,
command palette. Each reuses Phases 1–3 unchanged.

## Update the skill
After everything passes, append to the Learned patterns section of
`/mnt/skills/user/ag-code-instructor/SKILL.md`:
```
- conductor-core (2026): ERP trust slice. Golden rules are PRECEDENCE-ORDERED
  (correctness 0-4 outrank UX 5-12). Posting/tax/FX live in DB procedures as the
  source of truth; API is thin and only does scope+shape+gating. Field security =
  delete from payload (default-deny), never UI-hide. Mutability is DATA
  (field_mutability table), not if/else. FX frozen at post. AI writes only via
  human-accept reusing the guarded path (source='ai', accepted_by set). Every
  invariant check maps to a numbered rule and runs in `make verify`.
```

## Done.
The slice proves the model end to end on Sales Orders. Hand the same Phases 1–3 to
the next module and the trust layer comes for free.
