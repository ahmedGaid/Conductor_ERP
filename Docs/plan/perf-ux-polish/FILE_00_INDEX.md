# Performance & UX Polish — Master Index

> Fixing the brand-philosophy-review findings (Sessions A–H, 2026-07-20).
> **121 findings: 32 P1 (break) · 57 P2 (off-brand) · 32 P3 (polish).**
> Priority: all P1s first (trust/transparency blocking), then P2s (brand coherence), then P3s (nice-to-have).
> Does NOT block customer handover — feeds v1.1 polish. Founder-paced.

---

## Session structure

**Phase 1: P1 fixes (breaking trust)** — 9 sessions, ~2 weeks

| File | Domain | Findings | Effort | Est |
|---|---|---|---|---|
| FILE_01 | E-invoice | False ETA claims, missing copy hedge | 1–2 hr | 1 |
| FILE_02 | Workflows | Instances unreachable, dark theme, conversation clip, React Flow watermark | 2–3 hr | 2 |
| FILE_03 | Help/FAB | FAB overlaps Send button; help panel missing search + guide link | 1–2 hr | 1 |
| FILE_04 | Settings nav | Header false promise + split admin tabs, role 0 count, users machine-account leak | 2–3 hr | 2 |
| FILE_05 | Settings/API | Developers route list unfiltered, webhooks 34 events untranslated | 2 hr | 2 |
| FILE_06 | Purchasing | 4 Arabic words→1, PR status colors, `/purchasing/orders` route, converted-request "needs approval" label | 2–3 hr | 2 |
| FILE_07 | Sales | 2 Arabic words→1, quotation detail missing fields + wrong label | 2 hr | 2 |
| FILE_08 | CRM | Activity history UI, "Mark won" confirm + undo, status/leads terminology, campaign code field | 3–4 hr | 3 |
| FILE_09 | Inventory | Batches expiry sort/filter/days-remaining, stock-count variance pre-post show | 2–3 hr | 2 |

**Phase 2: P2 fixes (off-brand, systemic)** — 5 sessions, ~1.5 weeks

| File | Focus | Findings | Effort |
|---|---|---|---|
| FILE_10 | Create forms | Expand-by-default in 7 modules (one refactor) | 2–3 hr |
| FILE_11 | Money display | "EGP" hardcoded on every cell; USD 4-dp; RTL symbol flip (search+replace + locale handling) | 2–3 hr |
| FILE_12 | Plurals + i18n | Arabic `{{count}}` agreement (2 modules); English narration in Arabic UI (5 instances) | 2 hr |
| FILE_13 | Button/badge color | Filled red on non-destructive; colour on neutral states (brand alignment) | 2 hr |
| FILE_14 | Dark mode polish | Workflow canvas already in FILE_02; missing theme coverage (report builder, settings) | 1–2 hr |

**Phase 3: P3 fixes (polish)** — 3 sessions, ~1 week

| File | Focus | Findings |
|---|---|---|
| FILE_15 | Empty states | Generic "No data" → designed empties (6 screens) |
| FILE_16 | Keyboard + performance | Prefetch on hover, Suspense boundaries, missing aria labels |
| FILE_17 | Responsive + accessibility | Mobile breakpoints, color contrast, focus indicators |

---

## Model changes (breaking new sessions, merge gated)

**Chart of Accounts bilingual (FILE_07 dependency):**
- Add `name_ar` + `name_en` fields to `Account` model (split from single `name`)
- Create migration: backfill `name_ar = name`, reset `name_en = ""`
- Update seeding: `seed_accounting.py` seeds both `name_en` + `name_ar`
- Scope: accounting module only (other entities like Role/Branch deferred to Phase 2)
- Acceptance: `pytest erp/accounting --cov`; gate runs green; seeded COA readable in ar/en

---

## Document scope (what each FILE owns)

### FILE_01: E-invoice honesty
- Remove false ETA UI promises from `/einvoice` copy (ar.json + en.json)
- Update module description to match simulated behavior (phrase: "simulate" or "preview", not "submit")
- Reword action copy (not "إرسال للمصلحة" but "محاكاة" or similar)
- Update docstring in `eta_adapter.py` and `eta_client.py` to clarify stub status
- Acceptance: `check-i18n-parity.mjs` green; brand-feel checklist confirms no false promises

### FILE_02: Workflow UX (instances + canvas + titles)
- Add `/api/workflows/instances` list route + `/workflows/instances/:id` detail
- Fetch + render workflow runs list on `/workflows` (count → clickable list)
- Workflow canvas dark theme: theming vars to `canvas.module.css` + node/grid/control colors
- Remove React Flow watermark (CSS `display:none` on `.react-flow-attribution`)
- Conversation title clip: CSS `text-overflow` by locale (RTL = clip from left, LTR = clip from right)
  - Or: truncate at optimal char position (JS, locale-aware)
- Acceptance: 32 runs clickable and openable; canvas readable light + dark; titles readable ar/en; watermark gone

### FILE_03: Help FAB + panel UX
- Reposition FAB from `bottom-right` to avoid Send button overlap
  - Current overlap 36×10 px; move FAB 50px left or lower
- Add search input to Help Center panel (filter guides by title/keyword)
- Add link to full user guide from Help panel footer
- Acceptance: FAB doesn't overlay Send button (pixels measured); search works; guide link visible

### FILE_04: Settings nav + permission display (model change: Account bilingual)
- Split Settings nav into two sections:
  1. Personal (Profile, Appearance, Dashboard, Navigation, Notifications, Accessibility) 
  2. Organization (Organization, Branches, Webhooks, Custom Fields, Developers, System, AI Usage) — admin-gated
- Update `SettingsNav.tsx` caption to match context (not one generic "yours alone" for all)
- Fix `/admin/roles` permission count: query should return actual role's counted permissions (not 0 for superuser)
  - Or: note "unlimited" for System Admin with a visual distinction
- Filter `/admin/users` to hide service accounts (rows where `username` starts with `apikey:`, `ai_eval_`, `drill_`)
- Acceptance: nav reflects actual tab scope; roles page honest about counts; user list is human-only

### FILE_05: Settings/Developers (API + Webhooks i18n)
- Scope `/api/developers/routes` response to key's actual permissions (request permission map, filter endpoint list)
  - Or: note "All routes available to this key" if true, with LINK to audit log
- Translate 34 webhook event names: add `webhooks.<event>` keys to ar.json + en.json
  - Organize by category (sales.*, purchasing.*, accounting.*, etc.)
- Acceptance: `check-i18n-parity.mjs` green; routes list sensible; webhooks panel is ar/en

### FILE_06: Purchasing fixes (words + colors + routing)
- Purchasing Arabic word inventory:
  - Canonical: use `الطلب` (order, singular) everywhere
  - Replace: `أوامر التوريد` → `الطلبات`, `تفاصيل الطلب` → same, `طلبات` (in toasts) → `الطلبات`
  - Request: use `الطلب` with context (module name "Purchasing Requests")
- Extend `purchasingTone()` in `lib/statusTone.ts` to include request statuses (draft, submitted, approved, rejected, converted)
  - PR draft = gray, submitted = orange, approved = green, rejected = red
- Add route alias: `/purchasing` → `/purchasing/orders` (so parent path lands on list, not Home)
- Fix `PurchaseRequestDetailPage.tsx:231` — don't render static `requires_approval` flag as live state
  - Show "يحتاج موافقة" ONLY if `requires_approval && !approved`
- Acceptance: `npx tsc --noEmit` green; PR statuses distinct colors; `/purchasing` routes correctly; tone values consistent

### FILE_07: Sales fixes + Account bilingual migration
- Sales Arabic word inventory:
  - Canonical: use `الطلبات` (orders) everywhere
  - Replace: `أوامر البيع` in `sales.customer.viewOrders` + `related.orders` → `الطلبات`
- Quotation detail fixes:
  - Add timeline section (if exists in order, exists in quotation)
  - Add validity/expiry date display
  - Fix line-table heading: `تفاصيل الطلب` → `تفاصيل العرض` (quotation details, not order)
  - Remove orphaned `الموافقة` label (check if quotation has approval concept — if not, remove)
- **Execute Account bilingual model change:**
  - New migration: add `name_ar`, backfill from `name`, clear `name_en`, update `name` to unique constraint
  - Update seeding + tests
  - Update form + detail pages to show both fields
- Acceptance: `pytest erp/accounting` green; quotation detail readable + complete; order/quotation words distinct

### FILE_08: CRM fixes (activity + confirm + terminology)
- Implement activity history rendering on opportunity detail
  - Fetch `Activity` model data from API (add endpoint if missing)
  - Design + render timeline (calls, emails, meetings, tasks, notes)
- "Mark won" action: add ConfirmDialog before posting sales order
  - Warn: "This will create a sales order. You can undo it in Sales."
  - Implement Undo (soft delete + recovery, or API rollback)
- Fix `LeadsPage` + `TicketsPage` status column i18n keys
  - Use correct key: `crm.lead.status` / `crm.ticket.status`, not `crm.opp.stage`
- Add campaign code field to lead + opportunity detail forms
  - Read from `campaign.code` list, render as ComboBox
- Fix opportunity/salesfquotas terminology:
  - Use `الفرص` (opportunities) everywhere, not `الصفقات` (deals) on one screen
- Acceptance: Activity timeline renders; "Mark won" shows confirm + undo; terminology consistent; campaign code exposed

### FILE_09: Inventory final fixes (batches + stock count)
- Batches expiry improvements:
  - Add column: "Days until expiry" (compute `expiry_date - today`)
  - Make column sortable (ascending = expire soon)
  - Add filter: "Expiry status" (expired, expiring within 30 days, fresh)
  - Add primary action: "Use oldest first" (sort by expiry, show qty available by batch on receive)
- Stock count variance display:
  - BEFORE posting confirmation, show variance summary:
    - Items with variance (expected vs counted)
    - Per-warehouse totals
    - GL impact preview
  - User confirms "Post with these adjustments" (irreversible, shows consequence)
- Acceptance: Batches list has expiry sort + filter; stock-count shows variance before posting; both work ar/en

---

## Acceptance per FILE

Each FILE must pass:
1. **Gates:** `npx tsc --noEmit`, `node scripts/check-i18n-parity.mjs`, brand-feel checklist (conductor-brand skill)
2. **Smoke test:** drive the feature live (light+dark, ar+en, mobile if responsive)
3. **No regression:** run full `pytest` suite (no new failures)
4. **Commit:** conventional message, reference the plan session

---

## Phase integration

- **Phase 1 (FILE_01–09):** P1 fixes only. No scope creep.
  - Merge checkpoint after FILE_09: full gate suite, then merge to main
- **Phase 2 (FILE_10–14):** P2 systemic fixes
  - Merge checkpoint after FILE_14: gates green, merge to main
- **Phase 3 (FILE_15–17):** P3 polish
  - Final merge after FILE_17

---

## Known blockers / decisions

1. **Account bilingual (FILE_07):** A model change. Requires migration. Scope limited to accounting for v1.1.
   - Roles/Branches/Departments/Price Lists deferred to Phase 2 or later (larger, cross-module).
2. **Activity history (FILE_08):** API types exist. Rendering is pure UI. No backend work.
3. **"Mark won" Undo (FILE_08):** Soft-delete recovery? API rollback? Decide before FILE_08 starts.
4. **Workflow instances (FILE_02):** New route + DB query. Scoped: list view only (detail reuses existing `/instances/:id`).

---

## Why this order

- **P1s first:** Trust is the foundation. Fix all breaking-transparency issues before moving on.
- **By domain:** Group related modules (Purchasing 3 fixes together, Sales 2 together) so context stays warm.
- **Model changes last within phase:** Chart of Accounts (FILE_07) is a model change; run it after string/routing fixes so prior sessions aren't blocked.
- **P2 systemic after:** Once all breaking issues are fixed, batch the recurring patterns (forms, money, plurals, colors).
- **P3 polish last:** Nice-to-haves don't block anything; queue them for founder discretion.

---

## Merge strategy

- Work all Phase 1 files on branch `feat/perf-ux-p1`
- After FILE_09 passes all gates: merge to main, update `erp-status`
- Work Phase 2 on `feat/perf-ux-p2`
- Phase 3 on `feat/perf-ux-p3`
- Or: one branch for the whole plan if sessions run back-to-back

---

## One file per session (discipline)

Each FILE is ONE working session. No multi-file sessions. When a FILE is done:
1. Run gates + smoke test
2. Commit (reference FILE_NN)
3. Rename file to `FILE_NN_*_done.md`
4. Update `erp-status`: current position + NEXT file
5. Tell user: fresh session for next

---

## Queue position

Insert into `EXECUTION_ORDER.md` after pos 8D (post-handover-v1_1). Pos number TBD by founder (likely pos 13 or "PP" parallel-track).

---

## Next: Start FILE_01
