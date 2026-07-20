# Brand Philosophy Review — Master Index

> **Review the ENTIRE app against the Product Philosophy front door**
> (`Docs/Brand/Conductor_Product_Philosophy.md`, created 2026-07-18) and the triad it points to.
> Not a redesign — a **judgment audit**: drive every screen, score it against the 8 Conductor
> Standard, file ranked findings. Fixing is a SEPARATE pass (findings → their own sessions).

## The rubric (score every screen against these)
The 8 Conductor Standard = the ship test. Re-asked as the 7 decision-questions per screen:
1. **Invisible complexity** — one obvious thing, one primary action?
2. **Instant performance** — feels instant, no spinner where cached data could paint?
3. **Calm by default** — monochrome chrome; colour only inside the work, paired with word/icon?
4. **Trust through transparency** — says what happens *before*, reassures *after*, reversible?
5. **Consistency** — same action behaves the same everywhere?
6. **Human AI** — AI bits notice/explain/protect, drafts-only + gated (N/A if none)?
7. **Craft** — type, spacing, motion, Arabic language, errors feel designed?
8. **Business confidence** — user leaves more informed and in control?
Plus the closer: **"Would Linear ship this?"** — an honest "no" = a finding.

## Output per screen (uniform, so it rolls up)
`screen · one-line verdict · which Standard(s) fail · severity (P1 break / P2 off-brand / P3 polish)
· the specific fix`. Findings roll into the scorecard artifact.

## Review sessions (drive the real UI, ar + en, light + dark)

| Session | Surface | Screens |
|---|---|---|
| **A** | **App frame + global states** (shell, sidebar, sticky header, ⌘K, notifications, login, empty/error/loading/no-permission taxonomy, error boundary) | cross-cutting |
| **B** | **Accounting** | 16 (dashboard, journals, TB, GL, IS, BS, cash-flow, VAT, assets, cost-centers, bank-rec, budgets, report-builder) |
| **C** | **Inventory** | 10 (items, warehouses, movements, stock-on-hand, counts, batches) |
| **D** | **Sales** | 9 (orders, order→invoice, quotations, customers) |
| **E** | **Purchasing** | 8 (orders, import, requests, suppliers) |
| **F** | **CRM** | 7 (pipeline/kanban, opportunities, leads, tickets, campaigns) |
| **G** | **Settings + Admin + Pricing** | 16 (profile, appearance, dashboard, nav, notifications, a11y, org, branches, webhooks, custom-fields, developers, users, roles, pricing) |
| **H** | **Assistant + Help + E-invoice + Workflows** | assistant/knowledge/ops, help center, /einvoice, workflows/instances |

~85 routes total. One session = one surface = one sitting. Ar+en, light+dark each.

## Method per session (deterministic)
1. Recall `conductor-brand` (rubric + Arabic lexicon) + `erp-frontend` (what's normal).
2. Run the app (`run-dev.ps1`, login `admin`/`Dev12345!`). Drive each screen in the surface.
3. For each: answer the 7 questions honestly; note every "no" as a finding with severity + fix.
4. Check the Arabic specifically against Identity §6 (one canonical word, human status, blame-free
   error) — this is where craft usually slips.
5. Append findings to the scorecard artifact (see below). Do NOT fix in this pass.

## The tonight deliverable
`brand-review-scorecard` artifact — the rubric + full inventory + systemic findings already known
from the QA audit, published so the founder can skim tonight. Per-screen scores fill in as sessions
A–H run. (Built 2026-07-18.)

## Systemic findings already known (seed the scorecard — from the QA audit)
- **No app-wide error boundary** → any render crash = white screen. Fails Standard 4 + 7 globally.
  (Fix owned by `pre-handover-hardening/FILE_03`.)
- **Most routes not code-split** (App.tsx eager-imports ~40 pages) → slower first paint. Tension
  with Standard 2 (instant). Candidate finding for Session A.
- E-invoice status copy must not *claim* live ETA submission (Standard 4 + Brief §12 claims
  discipline) — verify in Session H. (Decision owned by `pre-handover-hardening/FILE_01`.)
  **VERIFIED BROKEN, Session H 2026-07-20** → scorecard §04j P1. The claim is made in full, in both
  locales, over a `simulates`-by-docstring adapter; `eta_client.py` is not wired into `issue.py`.

## Change log
- **2026-07-20 — Session H DONE (Assistant + Help + E-invoice + Workflows) — REVIEW PROGRAM COMPLETE.**
  9 routes + 3 overlays driven ar/RTL + en/LTR, dark + light (assistant, knowledge, ops, /einvoice,
  workflow list, canvas new + existing, an execution instance, user guide + glossary, Help Center
  panel, shortcuts dialog, docked assistant panel). **5 P1 · 11 P2 · 4 P3 + 1 pass block** →
  scorecard §04j. Headline — **the seeded finding is confirmed, and worse than seeded**:
  `/einvoice` claims live ETA filing end to end with no hedge in either locale (module description
  *"أرسل فواتيرك إلكترونيًا إلى مصلحة الضرائب المصرية"*, action *إرسال للمصلحة*, toast *تم إرسال
  الفاتورة*, column *معرّف المصلحة* / "ETA UUID", resting status *صالحة*), while
  `eta_adapter.py` says in its own docstring that it **simulates** — `submit()` always accepts,
  `query()` always returns `valid`, and the UUID is a local SHA-256 prefix printed as a government
  reference number. The new `eta_client.py` is **not wired into `issue.py`**, so real credentials
  change nothing. Second P1: **32 workflow runs exist, are counted on the list, and none can be
  opened** — no instances list route, the count is plain text, and `/instances/:id` is reachable
  only by pressing Run; the automation module cannot answer "did last night's run work?". Third P1:
  **the workflow canvas has no dark theme** (white grid/node/minimap/controls inside the black app)
  and prints a literal **"React Flow"** vendor watermark. Fourth P1: **conversation titles clip from
  the wrong end whenever script ≠ UI language** — English rows read "…ed this document?" in Arabic
  and vice versa, so half the history is unidentifiable in either locale. Fifth P1: **the help FAB
  overlaps the assistant's Send button** — measured 36×10 px, both locales. Also: the ops chart
  encodes meaning in **colour alone**; three KPI tiles say "vs last month" and render no delta; the
  health screen prints **vendor part numbers** (`gemini/gemini-2.5-flash`, a raw
  `routing_ask_groq_meta-llama…` slug beside a bare `0%`); **the glossary teaches `أمر بيع`** — the
  exact word Session D filed as its P1 — and the assistant panel repeats it in a suggestion chip;
  the help system has **no search anywhere** and the panel has no link to the full guide. Recurrences:
  server-English narration in an Arabic screen (**4th**, the execution viewer's `advanced 'start' ->
  'script_1'` + raw JSON), "EGP" on every money cell (**4th module → systemic**), USD 4-decimal
  money (2nd). **The user guide, the glossary, the context Help Center, the knowledge base page and
  the assistant's empty/working states are passes** — the guide's *"ما الذي قد يحدث خطأ"* sections
  and the 38-term glossary are the best written Arabic in the product. Method note: log in with
  `input[autocomplete="username"]` / `[autocomplete="current-password"]` + `.fill()` (the inputs
  carry no `name`/`id`); `?` opens the **shortcuts dialog**, the Help Center is the `⋮` app menu →
  *مساعدة*; Vite was on **5174** again. Next: **the review program is finished — findings roll into
  fix sessions.**
- **2026-07-20 — Session G DONE (Settings + Admin + Pricing).** 17 routes driven ar/RTL + en/LTR,
  dark + light (13 settings tabs, users, roles, both pricing screens). **5 P1 · 8 P2 · 4 P3 + 1 pass
  block** → scorecard §04i. Headline: **every Settings tab is captioned "these preferences are yours
  alone and never affect other users"** (`SettingsNav.tsx:26`, one `settings.intro` for all 13 tabs)
  — including the seven `isAdmin`-gated org-wide tabs where you edit the company tax number,
  deactivate a branch that scopes every sales/stock record, or mint an API key; the Organization tab
  then contradicts the header two lines below it. An active false statement, both locales. Second P1:
  **`/admin/roles` reports System Admin has 0 permissions** (Accountant 58, Auditor 32, Branch Manager
  91) — the superuser path almost certainly bypasses the counted permission table, so the one screen
  that answers "who can do what" states a falsehood about the most powerful role. Third P1: **the user
  list mixes machine accounts in with people** — `apikey:b31b47bd` wearing **System Admin**,
  `ai_eval_runner`, `drill_user`, 3 of 9 rows, on a page titled "manage who can sign in". Fourth P1:
  **the Developers API reference claims to list what *this key* can reach and prints all 209 routes**
  unfiltered, with raw Django converters (`<uuid:pk>`) on a customer surface. Fifth P1: **34 webhook
  event names ship untranslated** (`sales.QuotationConverted` …) as one unsectioned wall of
  checkboxes — the largest untranslated block found in the review. Recurrences confirmed:
  **English-only names in an Arabic UI now reaches customer-created records** (roles, branches,
  departments, price lists — **5th**; needs one shared `name_ar`/`name_en` migration decision),
  create-form-expanded (**7th module**), colour spent on the default state (**2nd**). Also:
  **text size is configurable twice**, on Appearance (`حجم النص`) and Accessibility (`نص أكبر`), two
  Arabic words one concept; **AI usage is the only money in the product in USD**, 4 decimals, symbol
  flipping sides mid-sentence in RTL (`$0.0080 من 3.0000$`); the 13-tab strip **wraps in both
  locales**. **Empty states, field primitives, Organization settings and the System tab's
  degraded-worker row are passes** — the empty states are the best in the product (not one bare
  "No data" across 17 routes) and Organization states every setting's consequence before you touch it.
  Method note: log in with `locator.fill()`, **not `.type()`** — `.type()` on these inputs silently
  no-ops and the POST returns 400 (Session F's `.click()`-first note is necessary but not sufficient).
  Vite may bind **5174** when 5173 looks free — read the port from `Get-NetTCPConnection` rather than
  assuming. Next: **Session H (Assistant + Help + E-invoice + Workflows)** — the last session.
- **2026-07-20 — Session F DONE (CRM).** 7 screens driven ar/RTL + en/LTR, dark + light (pipeline
  table, pipeline board, opportunity detail, leads, tickets, campaigns, campaign detail).
  **5 P1 · 8 P2 · 5 P3 + 1 pass block** → scorecard §04h. Headline: **the CRM has no activity
  history** — `api/crm.ts` fully types `Activity` (call/email/meeting/task/note) and no page renders
  any of it, so opportunity detail is six facts plus a notes box and cannot show a single thing that
  happened with the customer. Second P1: **the "Mark won" bar primary silently posts a sales order
  into Sales** — `winOpportunity(id, lines.length > 0)`, no confirm, no mention in the toast, and the
  only action in the module without Undo (`OpportunityDetailPage.tsx:120-131`). Third P1: **leads and
  tickets label their status column `crm.opp.stage` — "المرحلة / Stage" — while the filter beside it
  says "الحالة / Status"** (`LeadsPage.tsx:281`, `TicketsPage.tsx:290`); 4th module in a row on the
  two-words-one-concept refusal. Fourth P1: **`crm.campaign.linkHint` tells the user to set a campaign
  code on a lead or opportunity — no form in the product exposes the field**, though the API accepts
  it, so hand-made campaigns report 0/0 forever. Fifth P1: opportunities are **الفرص** everywhere
  except campaign detail, which calls the same records **الصفقات** in the same metrics grid.
  Recurrences confirmed: create-form-expanded (**5th module → fix once**), "EGP" on every money cell
  (3rd), Arabic `{{count}}` plural agreement (2nd), filled-red button on a non-destructive action
  (2nd). **The Kanban board, `PriorityBar`, `crmTone()` and the undo-not-confirm contract are
  passes** — the board is the best-built surface in the module (keyboard path equal to drag, designed
  empty column, per-column sums, correct RTL, undo on drop). Method note: log in with `.click()`
  before `.type()` on both fields — a bare `.type()` on the password input silently no-ops and the
  POST returns 400; and give lists ≥5s before judging a skeleton (leads settles at ~4s with 37 rows,
  not stuck). Next: **Session G (Settings + Admin + Pricing)**.
- **2026-07-20 — Session E DONE (Purchasing).** 9 routes driven ar/RTL + en/LTR, dark + light.
  **3 P1 · 6 P2 · 4 P3 + 1 pass block** → scorecard §04g. Headline: **Purchasing ships four Arabic
  phrasings for "purchase order"**, and one of them collides with the module's own word for
  "purchase request" — the bulk toasts say `تمت الموافقة على {{count}} طلبات` for *orders*
  (`purchasing.toast.bulkApproved`), which is indistinguishable from `bulkReqApproved` for
  *requests*; plus `أوامر التوريد` in the module description printed on every purchasing page
  (`ar.json:412`), `تفاصيل الطلب` as the PO line-table heading, and `الطلبات` on supplier detail via
  the Sales-shared `party.*` keys. Second P1: **every purchase-request status renders in one
  colour** — `purchasingTone()` (`lib/statusTone.ts:15-21`) contains only *order* statuses, so
  draft/submitted/approved/rejected/converted all fall through to `pending`; **rejected looks
  identical to approved**. Third P1: **a converted request still says "يحتاج موافقة"** —
  `PurchaseRequestDetailPage.tsx:231` renders the static `requires_approval` policy flag as if it
  were live state (PO detail does it correctly at `PurchaseOrderDetailPage.tsx:387`). Also found:
  **`/purchasing/orders` is not a route** — the list is mounted at `/purchasing` while every child
  is `/purchasing/orders/*`, so the parent path hits the catch-all `Navigate to="/"` and silently
  lands on the dashboard (Sales uses `/sales/orders`). Three prior findings recurred: secondary
  document as a degraded copy of the primary one (quotation → request, 2nd), create-form-expanded
  (4th module), server-generated English narration in an Arabic statement (3rd). **PO detail and the
  import-invoice screen are passes** — the import screen is the best AI surface reviewed so far
  (drafts-only, gated, unhyped). Method note: theme/language flip needs a `page.reload()` after
  `goto` on a hash route or the settings page is still `جارٍ التحميل…` when the click lands.
  Next: **Session F (CRM)**.
- **2026-07-20 — Session D DONE (Sales).** 9 routes driven ar/RTL + en/LTR, dark + light.
  **2 P1 · 5 P2 · 2 P3 + 1 pass block** → scorecard §04f. Headline: **Sales ships two Arabic words
  for "order"** — canonical `الطلبات` in the sidebar/tabs/headings, but `أوامر البيع` in
  `sales.customer.viewOrders` (`ar.json:1168`) and `related.orders` (`ar.json:2492`), so the
  customers-list row action and the page it opens name the same records differently. Direct hit on
  the hard-refusal list; pure string fix. Second P1: **quotation detail is order detail with the
  good parts deleted** — no timeline, no validity/expiry date, an orphaned `الموافقة` label, and a
  line-table heading that literally reads `تفاصيل الطلب` / "Order details" (`ar.json:1363`).
  Two prior findings recurred: create-form-expanded-by-default (3rd module → systemic) and
  server-generated English narration in an Arabic UI (customer statement, same class as Session B's
  chart of accounts). **Order detail + the invoice document are the best screens reviewed so far** —
  logged as passes. Method note: run **one** headless session at a time — concurrent Playwright
  logins rotate the refresh token and produce phantom 401/500s on detail routes that do not
  reproduce in a clean single session. Theme/language flip via Settings → Appearance / Profile
  segmented buttons (`button:has-text("Light")`), confirmed by `documentElement.data-theme`.
  Next: **Session E (Purchasing)**.
- **2026-07-20 — Session C DONE (Inventory).** 6 routes + 3 detail screens driven ar/RTL + en/LTR,
  dark + light. **2 P1 · 8 P2 · 6 P3 + 1 pass block** → scorecard §04e. Headline: the **batches
  screen cannot answer "what expires next"** — expiry is inert text, no days-remaining, no sort,
  no filter, no primary action; and **stock-count variance is not rendered until after you post**
  (`StockCountDetailPage.tsx:127-128`), so the irreversible stock + GL adjustment is committed
  before the difference is ever shown. Two Session B findings recurred module-wide (create form
  expanded by default; "EGP" on every cell) — treat those as systemic, one shared fix each.
  Method note: the app uses **HashRouter** — drive `localhost:5173/#/inventory/...`, a plain
  `/inventory` path silently renders Home. Theme/language must be flipped through
  Settings → Appearance / Profile in the real UI (a direct PATCH to
  `/api/identity/preferences` returns 401 from page context). Next: **Session D (Sales)**.
- **2026-07-20 — Session B DONE (Accounting).** 14 routes driven ar/en × light/dark.
  **2 P1 · 9 P2 · 4 P3 + 4 passes** → scorecard §04d. Headline: the **chart of accounts ships
  English-only from `seeding.py`, which the first-run setup wizard runs** — and `Account` has a
  single `name` field, so bilingual account names are a model change + migration, not a string fix.
  Second P1: filled red `حذف` buttons on every report-builder row. Next: **Session C (Inventory)**.
- **2026-07-20 — Session A DONE (full pass).** App frame + global states driven live in ar/RTL and
  en/LTR, light + dark, with real pixel review. **1 P1 · 8 P2 · 7 P3 + 6 verified passes**, all in
  the scorecard §04c. Closed the 2026-07-19 coverage gaps (login, skeletons, ⌘K, not-found route).
  The two seeded systemic findings (error boundary, code-split) re-confirmed FIXED in source.
  Method notes for the next session: the in-app screenshot tool times out — use Playwright
  `chromium.launch()` headless from a throwaway `.cjs` **inside `apps/web`**; theme/language are
  server-backed `UserPreferences`, so drive them through Settings → Appearance / Profile
  (writing `localStorage` is silently overwritten on load). Next: **Session B (Accounting)**.
- **2026-07-18 — Created.** Review program + tonight scorecard. Positioned in `EXECUTION_ORDER.md`
  as pos **BR** (founder-paced, off critical path; does not block handover — it feeds v1.1 polish).
