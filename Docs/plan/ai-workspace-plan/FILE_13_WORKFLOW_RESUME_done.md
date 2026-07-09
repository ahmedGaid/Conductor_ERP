# SESSION 13 — Workflow Continuity: Detour, Return, Resume
# Files: apps/web/src/assistant/detour.ts (new), apps/web/src/assistant/AssistantProvider.tsx, apps/web/src/assistant/AssistantPanel.tsx, apps/web/src/assistant/SuggestionCard.tsx, erp/assistant/services/agent.py, erp/assistant/api/views.py, apps/web/src/api/assistant.ts, apps/web/src/i18n/locales/*.json, erp/assistant/tests/test_resume.py (new)

---

## Before You Start

1. Open `apps/web/src/assistant/SuggestionCard.tsx` (session 12) → the `deep_link` option's
   `expect` field (`{entity, query}`) — the contract this session fulfils.
2. Open `apps/web/src/assistant/context.ts` → `collectContext()` and the DocumentCrumb record
   getter — return detection reads these, nothing new is invented.
3. Open `erp/assistant/services/agent.py` → `meta.pending` written by the suggest path
   (session 12) and by proposals (session 10).
4. Open `apps/web/src/assistant/AssistantProvider.tsx` → persisted state keys; the detour state
   joins them.

"Do not write anything yet."

---

## The promise this session keeps

User uploads a PO → supplier missing → one click to Create Supplier → saves → assistant says
"Welcome back — supplier ABC Trading created. Continuing the purchase order." → extraction values
still populated, processing resumes at the exact paused step. **No re-upload, no "what were we
doing?", ever.**

## Task A — Detour state (client)

Create `apps/web/src/assistant/detour.ts`:

```typescript
// One active detour at a time — a guided errand, not a task queue.
export interface Detour {
  conversationId: number;
  messageId: number;                       // the SuggestionCard that sent us
  expect: { entity: string; query: string };
  returnTo: string;                        // path we left (from collectContext().path)
  startedAt: number;                       // stale after 30 min — then we ask instead of assuming
}
```

Store on `AssistantProvider`, persisted to `localStorage("assistant.detour")` so a full reload
mid-detour survives. `SuggestionCard`'s deep-link click sets it (and keeps the panel open in its
current mode — floating collapses to a slim pill on the target page: icon + "Waiting — creating
supplier…" via `assistant.detour.waiting`, expandable).

## Task B — Return detection

In `AssistantProvider`, one effect watching route + DocumentCrumb while a detour is active:

- **Success path:** the user lands on a detail page whose DocumentCrumb record type matches
  `expect.entity` (create form → save → app already navigates to the new record's detail page —
  verify this on the supplier/customer/item forms; it is the standard pattern). Capture the
  record's id/label → this is the created record.
- **Manual path:** the waiting pill always offers "I'm done" and "Cancel" buttons — done triggers
  the same resume with no captured record (server re-resolves by `query`); cancel clears the
  detour and tells the conversation plainly.
- **Stale path:** detour older than 30 min → don't auto-resume; the pill becomes "Still creating
  the supplier?" with resume/cancel.

On success: navigate back to `returnTo`, then call Task C's resume endpoint. Navigation the
assistant initiates always announces itself in-chat first (the session-12 explanation already
promised it — the return completes that sentence).

## Task C — Resume execution (server)

- `POST /api/assistant/detours/resume` — body `{conversation_id, message_id, resolved:
  {entity, id, label} | null}`. Marks the suggestion `meta` resolved (SuggestionCard settles),
  then re-enters the agent loop with a synthetic system-side user turn recorded honestly in the
  transcript as `meta.kind = "detour_return"`:

  > "Detour complete: supplier ABC Trading (SUP-0042) now exists. Resume the pending work."

- The loop reads `meta.pending` from the suggestion message (the paused payload — extraction
  proposal, order draft args, import mapping), re-runs ONLY the failed resolution against the new
  record, and continues exactly where it stopped: re-validate → re-propose (session 10 card) or
  next pipeline stage (session 14 import). `resolved: null` ⇒ the loop re-runs the original
  lookup tool by `query`; still missing ⇒ it says so calmly, suggestion un-settles.
- Response streams over the standard SSE (reuse `ChatView`'s generator via a shared helper) so the
  welcome-back message ("Welcome back — I can see you created…") types like any reply.

## Task D — Attachments & extraction survive the detour

Verify (and fix if broken): `meta.pending` for extraction-born flows carries the extraction
proposal + `attachment_ids` — never raw file re-reads. Resume must not re-call the vision
provider; it reuses the persisted proposal and only re-resolves the blocked reference. Add a test
asserting zero `complete_json`/vision calls for the already-extracted parts on resume.

## Task E — i18n + tests

Both locales: `assistant.detour.waiting`, `done`, `cancel`, `cancelled`, `stale`, `welcomeBack`
(interpolated: entity + label), `resumed`.

`erp/assistant/tests/test_resume.py`: resume with resolved record → suggestion settled, pending
re-validated, proposal card emitted; resume with null + now-existing record by query → same;
resume with record still missing → calm miss, suggestion active again; detour_return turn visible
in transcript meta; extraction resume makes no vision call.

---

## Smoke Test

- [ ] Full PO story end-to-end: upload → missing supplier → deep link → create → auto return →
      "welcome back" names the supplier → proposal card with the ORIGINAL extracted lines intact
- [ ] Reload the browser mid-detour → pill still waiting; flow still completes
- [ ] Cancel from the pill → conversation states it plainly; suggestion card stays actionable
- [ ] "I'm done" without saving anything → assistant reports it's still missing, no false resume
- [ ] 30-min-stale detour asks instead of auto-resuming
- [ ] Arabic run of the full story — welcome-back grammar correct
- [ ] `pytest erp/assistant` + i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_14_FILE_IMPORT.md and continue
```
