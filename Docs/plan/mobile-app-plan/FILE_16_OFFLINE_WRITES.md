# SESSION 16 — Offline Writes & Sync
# Files: apps/mobile/lib/data/datasources/local/write_queue.dart (new), erp/core or module API
#        idempotency support (additive), FormScreen/action integration (surgical edits)

**Objective:** complete the offline story — mutations made on a dead network are queued durably,
replayed exactly-once when connectivity returns, and conflicts are surfaced honestly (server
wins, user informed, data never silently lost). Scope is DELIBERATE: queue the safe, common
verbs (create customer/supplier/lead, add attachment [already done], record receiving counts,
approve/reject where idempotent, save drafts); posting/financial mutations (issue invoice,
payments) remain online-only with a designed explanation — a phone must never invent a fiscal
document number offline. This boundary is a FEATURE; write it into DECISIONS.

---

## Before You Start

1. Re-read session 04's cache + session 13's upload queue (patterns to match, not duplicate).
2. Backend idempotency audit: for each queued verb, does the endpoint tolerate replay? READ each
   one. The fix is a standard `Idempotency-Key` header: a small server-side table
   (key → response snapshot, per user, TTL 48 h) checked in a DRF mixin/decorator applied to the
   queueable endpoints — additive, tested. Design it once in `erp/core` (or wherever
   cross-module API helpers live — READ the codebase's convention).
3. Session 09/10 offline-blocked states — the screens this session upgrades.
4. Connectivity signal: the session-04 `NetworkInfo` HTTP probe (`flutter-lessons` issue 1) on
   demand + a lifecycle-resume trigger. Treat "connected" as a hint; only a successful replay is
   truth. NO background-execution dependency in v1 — foreground triggers (connectivity restored,
   app resume, post-enqueue) are primary; a background isolate/WorkManager path is added later
   ONLY if field measurement shows foreground replay isn't enough (then a DECISIONS entry).

"Do not write anything yet."

---

## Task A — Backend idempotency (additive)

1. `IdempotencyKeyMixin`: on `Idempotency-Key` header — first time: execute, store status+body
   snapshot; replay: return the snapshot, execute NOTHING. Scoped per user. Table cleaned by TTL.
2. Apply to the queueable endpoints identified in the audit (explicit list written into this
   session's commit message). Tests: double-POST with same key = one record + identical
   response; different keys = two records; cross-user same key = isolated.

## Task B — Write queue (drift `write_queue` table + runner)

1. drift table `write_queue(id, verb, endpoint, payload, idempotencyKey, chainId, status,
   attempts, createdAt, errorKey)`. Status: pending → sending → done | conflict | failed.
   Datasource uses the `_ready` init pattern (`flutter-lessons` issue 3).
2. Runner: strictly FIFO per queue (ordering matters: create customer BEFORE the lead that
   references it — same-session dependent writes share a `chainId` and a chain stops on first
   failure); triggers: connectivity restored, app resume, post-enqueue. Single-flight (one
   runner, ever — a `Completer`-guarded singleton). Backoff on 5xx/network; NO retry on 4xx
   (that's a conflict/validation outcome, not a network problem).
3. Outcomes:
   - 2xx → done; invalidate affected cache keys; quiet toast if app foregrounded ("تم الحفظ —
     كان في انتظار الاتصال").
   - 409/validation → `conflict`: kept in an **Outbox** screen (More → "في الانتظار"): each row
     shows what was attempted, the server's translated reason, and actions — edit & retry
     (reopens the FormScreen prefilled), or discard (AppDialog). Server wins; the user decides
     the retry. Nothing silent, nothing lost.
4. Optimistic reads: queued creates appear in lists from a cache overlay tagged "بانتظار
   المزامنة" (StatusChip) so the field worker trusts the app; overlay resolves on replay
   (in-place list updates, `flutter-lessons` issue 5).

## Task C — Screen integration

1. FormScreen: when offline and the verb is queueable → submit becomes "سيُحفظ عند الاتصال"
   (designed, honest) → enqueue. Non-queueable verbs keep the session-09 online-required state.
2. Approvals (session 10): approve/reject become queueable ONLY if the Task A audit proved
   idempotent semantics AND staleness guards exist (send the document's version/updated_at;
   server rejects stale → conflict path). Otherwise they stay online-only — correctness over
   demo value.
3. Outbox badge on More tab when non-empty; Outbox empty state is a designed "كل شيء متزامن".

---

## Smoke Test

- [ ] Airplane mode: create 2 customers + a receiving count → all visible with pending chips →
      network back → replay in order → web shows all three, exactly once
- [ ] Kill the app with a non-empty queue → reopen → replays
- [ ] Same-key double replay forced (crash between send and mark-done: simulate by killing the
      runner mid-flight) → server has ONE record (idempotency proven end-to-end)
- [ ] Conflict: create a customer offline whose name web took meanwhile (unique rule — use
      whatever web actually enforces) → Outbox row with translated reason → edit & retry → done
- [ ] Chain: offline customer + dependent record → both land, order preserved; force first to
      conflict → second waits, chain visible in Outbox
- [ ] Invoice issue attempt offline → still the honest online-required state (boundary holds)
- [ ] `pytest` green on idempotency tests; analyze + test + parity green; PARITY.md offline rows
      flipped

## Risks

- THE most bug-prone session of the plan. If the audit or chains blow the timebox, cut scope to
  independent single writes (no chains) and record the cut — a small correct queue beats a big
  eventual one.
- Clock-skewed devices corrupting staleness guards → versions/updated_at come from server data,
  never device clocks.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_17_PERFORMANCE_AND_A11Y.md
Phase 3 complete — natural merge checkpoint.
```
