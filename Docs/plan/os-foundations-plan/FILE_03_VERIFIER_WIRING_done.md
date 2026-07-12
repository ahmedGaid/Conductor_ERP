# FILE_03 — L1: Wire the verifier into every agent write

> ONE SESSION. Prereq: FILE_01 + FILE_02 `_done`.
> Touches the confirm endpoint + a small proposal-card UI addition (verdict line).

## Why

FILE_02's packs mean nothing until every confirmed agent action runs them. This file makes the
loop: execute → verify → (ok: honest verdict on the card) / (fail: automatic rollback +
compensation note + honest report). It also makes re-confirms safe via the L0 idempotency keys.

## The execution contract (target state of the confirm path, views.py L302–342)

```
confirm arrives
  → idempotency check: same action + same natural key already confirmed recently? → return the
    prior result, execute nothing (retry-safe)
  → with transaction.atomic():
        result = actions.execute(actor, name, payload)
        report = verifier.run(action.invariants, scope={links, payload, actor})
        if not report.ok: raise VerifierFailed(report)   # atomic unwinds the write
  → ok:   proposal["verifier"] = {"ok": true, "packs": [...]}; audit verdict; card shows "checked"
  → fail: nothing persisted (rollback IS the compensation for this phase's draft-risk actions);
          proposal stays pending + reusable; card shows the blame-free report; audit records the
          failure with the findings
```

Notes:
- **Rollback-as-compensation:** every current action is `draft` risk, so unwinding the atomic
  block fully undoes it — the `compensation` action field stays declared-but-unused until a
  `post`-risk action ships (Phase B). A comment in the code says exactly this.
- **Verifier failure is OUR bug, not the user's.** Copy is blame-free: "The draft could not be
  saved because a check failed (totals did not match). Nothing was written." + the findings.
- The verifier runs INSIDE the atomic block — it sees the write, and its failure unwinds it.
  Packs are read-only (FILE_02), so they cannot dirty the transaction.

## Tasks

### [x] T3.1 — Idempotent confirms

- **Goal:** replaying a confirm (double-click, network retry, agent retry) never writes twice.
- **Files:** `erp/assistant/services/actions.py`; `erp/assistant/api/views.py`;
  `erp/assistant/tests/test_actions.py`.
- **Steps:**
  1. `actions.idempotency_key(name, payload) -> str` — sha256 over the action name + the
     payload values named by the action's `idempotency` tuple (L0). Empty tuple → key over the
     whole payload.
  2. The existing single-use guard (`proposal["status"] != "pending"` → `ActionAlreadyHandledError`,
     views.py L314) already blocks same-card replays. Add the cross-card case: before execute,
     look for another confirmed proposal with the same key in this user's messages from the last
     10 minutes (query `Message.meta` — same pattern the view already uses); hit → return that
     result with `"deduplicated": true`, execute nothing.
  3. Audit the dedupe (`action="confirm_deduplicated"`).
- **Accept:** test: build + confirm the same sales-order proposal twice via two separate messages
  → one `SalesOrder` row, second response flagged `deduplicated`.
- **Output:** agent retries are safe — the precondition for any future autonomy level.

### [x] T3.2 — Verify-after-execute + rollback on failure

- **Goal:** the contract block above, live for all 17 actions.
- **Files:** `erp/assistant/api/views.py` (confirm path); NEW exception in
  `erp/assistant/services/` or reuse errors module; `erp/assistant/tests/test_actions.py`.
- **Steps:**
  1. Wrap execute + verify in one `transaction.atomic()` exactly as the contract block shows.
     Actions with empty `invariants` (the 13 defaults) skip the verify call — zero behaviour
     change for them.
  2. On `Report.ok`: store `proposal["verifier"]`, include it in the response envelope, audit as
     part of the existing confirm record (`after={"summary":…, "verifier": …}`).
  3. On failure: catch `VerifierFailed`, leave proposal `pending`, respond 422 with the blame-free
     message + findings, `audit.record(action="verifier_failed", after={findings})`.
- **Accept:** tests: (a) confirm a balanced journal draft → response carries
  `verifier.ok == true`; (b) monkeypatch a pack to fail → the write rolled back (row count
  unchanged), proposal still pending, audit row exists; (c) an invariant-less action confirms
  exactly as before (regression).
- **Output:** every agent write is checked or explicitly unchecked-by-declaration. Trust ledger
  (moat #3) starts accumulating verdicts.

### [x] T3.3 — Verdict on the card (web)

- **Goal:** the proposal card shows the verifier outcome as one quiet line.
- **Files:** `apps/web/src/assistant/` proposal-card component (locate via the existing
  confirm-flow rendering); `apps/web/src/i18n/ar.json` + `en.json`.
- **Steps:**
  1. Confirmed card + `verifier.ok` → one line: ✓ "تم التحقق من القيود" / "Checks passed" with
     the pack count. Muted token color; color pairs with the word (monochrome-chrome rule).
  2. 422 verifier failure → the card's existing error surface shows the blame-free message; no
     new state machinery.
  3. Recall `conductor-brand` for the Arabic line before committing copy; add both keys.
- **Accept:** from `apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc -b` green; repo
  root `python scripts/gates/gate03.py` green.
- **Output:** the safety mechanics are *visible* — deep vision §6 ("safety restated as product").

## After this session

`pytest erp/assistant` + web gates green → commit
(`feat(assistant): os-foundations L1 — verifier wired into confirms`) → check boxes → rename
`_done` → update `erp-status` → fresh session for FILE_04.
