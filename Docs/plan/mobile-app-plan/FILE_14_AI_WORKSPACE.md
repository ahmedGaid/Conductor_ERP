# SESSION 14 — AI Workspace Parity
# Files: apps/mobile/app/(tabs)/assistant/**, apps/mobile/src/assistant/** (new),
#        apps/mobile/src/api/endpoints/assistant.ts (new)

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
3. Confirm SSE works with RN's fetch/XHR on both platforms (READ current guidance — streaming
   text via XHR `onprogress` is the classic RN approach; verify against the Expo/Hermes version
   in use; if a polyfill decision is needed it goes to DECISIONS).
4. Session 13's share-to-assistant stub.

"Do not write anything yet."

---

## Task A — Threads & messages (`(tabs)/assistant/`)

1. Thread list: same list web shows (same endpoint): search, pin, archive, rename (Sheet
   actions), relative times. Starting state = designed welcome (web's copy).
2. Conversation screen: streaming markdown-lite renderer — PORT web's in-house renderer
   (`apps/web/src/assistant/Markdown.tsx` equivalent) to RN Text/View primitives; same supported
   syntax, nothing more. Streaming bubbles token-by-token; cancel button while streaming;
   retry/copy/regenerate actions matching web.
3. Composer: multiline, attach (session 13's picker/camera/share-staged files → same assistant
   attachment endpoints), stop/send states. Keyboard handling matters here more than anywhere —
   test on small Androids.
4. Agent step progress: render the same step events web shows (plan → tool calls → validate)
   as a quiet collapsible trail — calm, no theatrics.

## Task B — Safe actions & detours

1. `ActionCard` port: proposed writes render as typed cards (what will happen, on which records)
   with confirm/reject — SAME confirm endpoints; the phone's card is a sibling of web's
   (`apps/web/src/assistant/ActionCard.tsx`). Confirm = destructive-grade interaction: Dialog +
   haptic. Result cards deep-link to created/changed records via session 06's `linkFor`.
2. Guided detours (ai-workspace 12–13): blocker suggestions arrive as cards with deep links into
   mobile screens + prefill. Wire prefill into FormScreens (a `usePrefill` analogue matching
   web's `lib/usePrefill.ts` contract). Detour resume: returning to the conversation after the
   fix resumes exactly as web does (server holds the state — mobile just navigates back).

## Task C — Context envelope & summon-anywhere

1. Port the client context collector: current route → module/record context (same envelope
   fields web sends — record type, id, visible filters). One hook: `useAssistantContext()`
   registered by RecordScreen/ListScreen patterns automatically — zero per-screen work.
2. Summon: assistant icon in every ScreenHeader (and cmd-K row on iPad) opens the assistant as a
   Sheet OVER the current screen (not a tab switch) pre-scoped to that record — "اسأل عن هذه
   الفاتورة". Same conversation store; the Sheet and the tab are two doors to one room.
3. Share-to-assistant (session 13 handoff): staged file becomes an attachment in a new
   conversation — the WhatsApp-PDF → extract → draft-invoice flow now works from a phone
   end-to-end through existing server pipelines.

---

## Smoke Test

- [ ] Same account, same thread visible on web and mobile; message sent from phone streams on
      phone and appears on web — continuity proven
- [ ] Streaming: long answer streams smoothly (no buffer-then-dump), cancel works mid-stream,
      ar text renders RTL inside markdown correctly
- [ ] Full flagship flow ON THE PHONE: share a supplier-invoice PDF from WhatsApp → assistant
      extracts → proposes draft → blocker (missing supplier) → detour card → create supplier
      (prefilled FormScreen) → auto-resume → confirm action card → invoice draft exists on web,
      audit trail correct (this is claims-gate demo #1, mobile edition)
- [ ] Record-scoped summon: open an invoice → assistant Sheet → "كم المتبقي على هذه الفاتورة؟" →
      correct contextual answer with no manual context given
- [ ] Permission truth: restricted user asks about a forbidden module → same refusal web gives
- [ ] Offline: assistant shows designed offline state (threads readable from cache, composing
      blocked honestly); tsc + parity green; PARITY.md AI rows flipped

## Risks

- SSE-on-RN is the technical risk → Before-You-Start item 3 resolves it BEFORE building UI; if
  streaming proves impossible without a dep, the DECISIONS entry weighs one — never silent
  degradation to non-streaming.
- Markdown port drift → share the same test fixtures web's renderer uses (copy the fixture file,
  assert same visible output classes of behaviour).

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_15_NOTIFICATIONS.md
```
