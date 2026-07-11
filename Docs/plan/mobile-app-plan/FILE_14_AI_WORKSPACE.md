# SESSION 14 — AI Workspace Parity
# Files: apps/mobile/lib/presentation/pages/assistant/**, assistant domain/data layers (new)

**Objective:** Conductor AI on mobile with FULL parity to the web workspace — same threads, same
streaming, same agent loop with step progress, same safe human-in-the-loop action cards, same
context awareness. Because conversations, tools, permissions, and the agent all live server-side
(ai-workspace plan sessions 01–15), this session is a CLIENT build: mobile renders the same
truth. The AI is not a chat screen — it knows what record you're looking at, and every screen
can summon it.

---

## Before You Start

1. Open `Docs/plan/ai-workspace-plan/FILE_00_INDEX.md` + the web implementation it produced:
   `apps/web/src/assistant/` (Provider, Panel, MessageList, Composer, ActionCard) and
   `apps/web/src/api/assistant.ts` → endpoint contracts: conversations CRUD, SSE chat, cancel,
   attachments, action confirm/execute, context envelope shape.
2. Open `erp/assistant/api/urls.py` → the live endpoint list (it has grown since the plan; the
   CODE is truth).
3. Prove SSE streaming in Dart BEFORE building UI: `dio` with `ResponseType.stream` (or raw
   `HttpClient`) → decode the byte stream → split SSE events incrementally. Write a 20-line spike
   against the real chat endpoint on BOTH platforms. If a dedicated SSE package is genuinely
   needed, that is a DECISIONS entry — never silent degradation to non-streaming.
4. Session 13's share-to-assistant stub.

"Do not write anything yet."

---

## Task A — Threads & messages (`pages/assistant/`)

1. Thread list: same list web shows (same endpoint): search, pin, archive, rename (AppSheet
   actions), relative times. Starting state = designed welcome (web's copy).
2. Conversation screen: streaming markdown-lite renderer — PORT web's in-house renderer
   (`apps/web/src/assistant/Markdown.tsx` equivalent) to Flutter `Text.rich`/`WidgetSpan`
   primitives; same supported syntax, nothing more (no markdown package — the subset is small
   and owned). Streaming bubbles token-by-token (append to state, `buildWhen` scoped to the
   streaming message — don't rebuild the whole list per token); cancel button while streaming;
   retry/copy/regenerate actions matching web.
3. Composer: multiline, attach (session 13's picker/camera/share-staged files → same assistant
   attachment endpoints), stop/send states. Keyboard handling matters here more than anywhere —
   test on small Androids (resize behaviour, `SafeArea`, IME action button).
4. Agent step progress: render the same step events web shows (plan → tool calls → validate)
   as a quiet collapsible trail — calm, no theatrics.

## Task B — Safe actions & detours

1. `ActionCard` port: proposed writes render as typed cards (what will happen, on which records)
   with confirm/reject — SAME confirm endpoints; the phone's card is a sibling of web's
   (`apps/web/src/assistant/ActionCard.tsx`). Confirm = destructive-grade interaction: AppDialog +
   haptic. Result cards deep-link to created/changed records via session 06's `linkFor`.
2. Guided detours (ai-workspace 12–13): blocker suggestions arrive as cards with deep links into
   mobile screens + prefill. Wire prefill into FormScreens (a prefill mechanism matching web's
   `lib/usePrefill.ts` contract — route extra carrying initial field values). Detour resume:
   returning to the conversation after the fix resumes exactly as web does (server holds the
   state — mobile just navigates back).

## Task C — Context envelope & summon-anywhere

1. Port the client context collector: current route → module/record context (same envelope
   fields web sends — record type, id, visible filters). One mechanism: an
   `AssistantContextScope` inherited widget registered by RecordScreen/ListScreen patterns
   automatically — zero per-screen work.
2. Summon: assistant icon in every ScreenHeader (and cmd-K row on iPad) opens the assistant as an
   AppSheet OVER the current screen (not a tab switch) pre-scoped to that record — "اسأل عن هذه
   الفاتورة". Same conversation store; the Sheet and the tab are two doors to one room.
3. Share-to-assistant (session 13 handoff): staged file becomes an attachment in a new
   conversation — the WhatsApp-PDF → extract → draft-invoice flow now works from a phone
   end-to-end through existing server pipelines.

---

## Smoke Test

- [ ] Same account, same thread visible on web and mobile; message sent from phone streams on
      phone and appears on web — continuity proven
- [ ] Streaming: long answer streams smoothly (no buffer-then-dump), cancel works mid-stream,
      ar text renders RTL inside markdown correctly, frame timeline stays clean while streaming
      (no per-token full-list rebuilds)
- [ ] Full flagship flow ON THE PHONE: share a supplier-invoice PDF from WhatsApp → assistant
      extracts → proposes draft → blocker (missing supplier) → detour card → create supplier
      (prefilled FormScreen) → auto-resume → confirm action card → invoice draft exists on web,
      audit trail correct (this is claims-gate demo #1, mobile edition)
- [ ] Record-scoped summon: open an invoice → assistant Sheet → "كم المتبقي على هذه الفاتورة؟" →
      correct contextual answer with no manual context given
- [ ] Permission truth: restricted user asks about a forbidden module → same refusal web gives
- [ ] Offline: assistant shows designed offline state (threads readable from cache, composing
      blocked honestly); analyze + test + parity green; PARITY.md AI rows flipped

## Risks

- SSE stream parsing edge cases (chunk boundaries splitting events/UTF-8) → the Before-You-Start
  spike resolves the mechanism BEFORE UI; unit-test the event splitter with adversarial chunk
  fixtures.
- Markdown port drift → share the same test fixtures web's renderer uses (copy the fixture file,
  assert same visible output classes of behaviour).

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_15_NOTIFICATIONS.md
```
