# Conductor AI Workspace — Master Index

## Project Goal

Grow the existing assistant (`erp/assistant/` + `apps/web/src/pages/assistant/`) into **Conductor AI**:
a persistent, context-aware AI workspace available on every page — threaded conversations, streaming
answers, file attachments, an agentic tool loop over the whole ERP, and safe human-in-the-loop
actions. Not a chatbot bolted on: another team member that already knows the page, the record, the
user, and the permissions. Quality bar: Linear's craft, Telegram's calm, ChatGPT-level polish.

**We extend what exists — never rebuild.** PR #31 already shipped: multi-provider client
(`complete_json` → Gemini / Groq / Anthropic), read-only tool catalog (`tools.py`), `/api/assistant/status`,
`/ask`, `/extract-document`, and a single-shot Q&A page with citations.

## Phases

| Phase | Sessions | Delivers |
|---|---|---|
| **1 — Foundations** | 01–03 | Conversation persistence, SSE streaming, context envelope |
| **2 — Workspace UI** | 04–07 | Global panel (floating/docked/fullscreen), threads, rich messages, attachments |
| **3 — Agentic layer** | 08–14 | Full tool catalog, multi-step agent loop, safe actions, page assistant, guided detours + resume, file import |
| **Close** | 15 | Acceptance + regression + polish |

## Session Map

| # | File | What gets built | Est. |
|---|---|---|---|
| 01 | FILE_01_CONVERSATIONS_BACKEND.md | Conversation + Message models, CRUD/search/pin/archive API | 25 min |
| 02 | FILE_02_STREAMING_BACKEND.md | Provider streaming, SSE `/assistant/chat`, cancel | 25 min |
| 03 | FILE_03_CONTEXT_ENVELOPE.md | Client context collector + server system-prompt builder + personas | 25 min |
| 04 | FILE_04_PANEL_SHELL.md | Global entry point, ⌘J, floating/docked/fullscreen panel shell | 25 min |
| 05 | FILE_05_THREADS.md | Conversation list: history, search, rename, pin, archive, delete | 25 min |
| 06 | FILE_06_MESSAGES.md | Markdown-lite renderer, streaming bubbles, retry/edit/regenerate/copy, follow-ups | 30 min |
| 07 | FILE_07_ATTACHMENTS.md | Drag-drop/paste/pick files into chat; image/PDF/CSV/XLSX understanding | 25 min |
| 08 | FILE_08_TOOL_CATALOG.md | Read tools across purchasing/inventory/accounting/CRM/workflows/audit | 30 min |
| 09 | FILE_09_AGENT_LOOP.md | Multi-step plan→tool→validate loop with streamed step progress | 30 min |
| 10 | FILE_10_SAFE_ACTIONS.md | Propose→confirm write actions with audit + result cards | 30 min |
| 11 | FILE_11_PAGE_CONTEXT.md | Embedded page assistant: current-record awareness, per-module prompts | 20 min |
| 12 | FILE_12_GUIDED_DETOURS.md | Actionable blockers: deep links, prefill, permission-aware options | 30 min |
| 13 | FILE_13_WORKFLOW_RESUME.md | Detour state, return detection, auto-resume with context intact | 30 min |
| 14 | FILE_14_FILE_IMPORT.md | Import intelligence: inspect → map → preview → confirm → report | 30 min |
| 15 | FILE_15_ACCEPTANCE.md | Full acceptance, regression, polish, gates, sign-off | 30 min |

Each `---` between phases is a natural checkpoint: finish the phase, merge, start a fresh session.

## Affected files (exhaustive)

Backend (`erp/assistant/` unless noted):
- `models.py` (new), `migrations/` (new), `api/views.py`, `api/urls.py`, `client.py`,
  `services/ask.py`, `services/context.py` (new), `services/agent.py` (new),
  `services/actions.py` (new), `services/suggestions.py` (new), `services/imports.py` (new),
  `services/files.py` (new), `tools.py`, `tests/` (new test modules per session)

Frontend (`apps/web/src/`):
- `api/assistant.ts`, `pages/assistant/AssistantPage.tsx`, `pages/assistant/assistant.css`
- `assistant/` (new dir): `AssistantProvider.tsx`, `AssistantPanel.tsx`, `ThreadList.tsx`,
  `MessageList.tsx`, `Composer.tsx`, `Markdown.tsx`, `ActionCard.tsx`, `SuggestionCard.tsx`,
  `ImportCard.tsx`, `context.ts`, `suggestions.ts`, `detour.ts`, `assistant-panel.css`
- `lib/usePrefill.ts` (new) + the supplier/customer/item create forms it feeds (additive prefill only)
- `app/AppShell.tsx`, `app/CommandBar.tsx`, `app/ShortcutsDialog.tsx`
- `i18n/locales/ar.json`, `i18n/locales/en.json`

## Never touch

- `erp/audit/models.py` — append-only; write only via `erp.audit.services.record(...)`
- `apps/web/src/styles/tokens.css` — no new raw hex; use existing tokens
- `apps/web/src/lib/money.ts` — money formats at the edge; don't add a second formatter
- Existing module `contracts.py` **signatures** (sales/purchasing/inventory/accounting) — add new
  helpers if needed, never change existing ones
- Other apps' migrations
- `DECISIONS.md` architecture: **tool-use, never free-text-to-SQL**. The original spec's "write SQL
  when needed" is explicitly rejected — every data access goes through a typed tool running as the
  current user (`actor`), so RBAC + data scope + audit always hold.

## Standing reference

`Docs/ARP_STRATEGY.md` governs category, scope, and team rules for every session in this plan —
this workspace IS the prerequisite for the ARP roadmap (`Docs/plan/arp-roadmap.md`), and sessions
12–13's detour demo is claims-gate demo candidate #1. When a session decision touches scope
(add/remove a capability), the strategy doc wins.

## Ground Rules (every session)

1. **Read before write.** Every session starts by reading the named files. Never write from memory.
2. **Additive.** Extend `tools.py`, `client.py`, `api/urls.py` — don't rewrite. `/ask`,
   `/extract-document`, `/status` keep working until the acceptance session says otherwise.
3. **AI runs as the user.** Every tool/action executes with `actor` = request user. No superuser
   shortcuts, no raw SQL, no bypassing contracts.
4. **Writes are human-in-the-loop.** The model proposes; a typed confirm step executes through the
   normal module contract + `audit.record`. The invoice→draft extraction flow is the template.
5. **Frontend hard rules:** design tokens only, logical CSS only (`inline-start/end`), every string
   a key in BOTH `ar.json` and `en.json`, no new npm dependencies (markdown renderer is built
   in-house in session 06), monochrome chrome, designed empty/error/loading states, settled motion.
6. **Gates before "done":** from `apps/web`: `node scripts/check-i18n-parity.mjs` and
   `npx tsc --noEmit`; repo root: `python scripts/gates/gate03.py`; backend: `pytest erp/assistant`.
7. **Done means renamed.** When a session's smoke test + gates pass and the work is committed,
   rename its file by appending `_done` (e.g. `FILE_01_CONVERSATIONS_BACKEND_done.md`). A `_done`
   file is **never opened again** — the next session is always the lowest-numbered file without
   the suffix. Fixes to shipped work happen in the CURRENT session against the code, not by
   revisiting an old plan file.
8. **Blockers are actionable (sessions 12+).** The assistant never stops at "X doesn't exist" —
   every dependency blocker ships as issue + fastest permitted fix + promised resume, and the
   detour returns the user to the exact paused step with all context intact. A suggestion without
   a working resolution path does not ship.

## How to use this plan

1. New Claude Code session → paste `FILE_00_INDEX.md` + the next `FILE_NN` file.
2. Claude does the session's "Before You Start" reads, then the tasks, then the smoke test.
3. Smoke test green → run the gates → commit → **rename the file with `_done`** → `/compact` →
   next file in a fresh session.
4. One session file = one Claude session. Never roll two files into one chat, never reopen a
   `_done` file — the plan folder itself shows the progress bar.

## After all sessions complete

- Run FILE_13 acceptance + regression checklists end-to-end in both languages (ar RTL first).
- Run the `conductor-brand` brand-feel checklist on the panel, threads, and action cards.
- Merge `feat/ai-workspace` → main; update the `erp-status` skill anchor.

*Generated by ag-plan skill. Do not edit this index manually.*
