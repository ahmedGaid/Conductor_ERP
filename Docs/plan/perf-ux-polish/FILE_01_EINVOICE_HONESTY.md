# FILE_01: E-invoice Honesty — Remove False ETA Submission Claims

**Session scope:** Remove false promises that `/einvoice` submits live to Egyptian Tax Authority.
The module simulates ETA submission (docstring: `eta_adapter.py` "simulates"), not wires real credentials.
Reword all copy to match reality (preview/simulate, not submit).

**Severity:** P1 — breaks Standard 4 (Trust through transparency). Currently claims live filing in both locales
over a stub adapter. User believes their invoices are submitted to government when they're not.

**Effort:** 1–2 hr (string fixes only, no model/route changes).
**Model fit:** Haiku (mechanical i18n sweep).

---

## Scope: Files to change

- `apps/web/src/i18n/locales/ar.json` — reword ETA action/module copy
- `apps/web/src/i18n/locales/en.json` — reword ETA action/module copy
- `erp/einvoice/services/eta_adapter.py` — update docstring to be honest
- `erp/einvoice/services/eta_client.py` — if docstring claims submission, fix it

---

## Findings detail (from Session H)

**Finding 1: Module description claims live ETA filing**
- Current: `مساعدة | أرسال فواتيرك إلكترونيًا إلى مصلحة الضرائب المصرية` (Send your invoices electronically to ETA)
- Reality: `eta_adapter.py` simulates ETA submission; real `eta_client.py` not wired into `issue.py`
- Fix: Reword to clarify: "محاكاة إرسال الفواتير" (Simulate sending invoices) or "معاينة الفواتير" (Preview invoices for ETA)

**Finding 2: Action copy says "submit to ETA" (إرسال للمصلحة)**
- Current toast: `تم إرسال الفاتورة` (Invoice submitted)
- Current action: `إرسال للمصلحة` (Send to ETA)
- Fix: Change to `محاكاة` (Simulate) or `معاينة` (Preview) depending on final product decision

**Finding 3: Status column labeled with ETA acronym + "معرّف المصلحة" (ETA ID)**
- Current: Shows UUID as if it's a government reference number
- Reality: Local SHA-256 prefix, not a government ID
- Fix: Relabel column to `معرّف محلي` (Local ID) or `معرّف المحاكاة` (Simulation ID)

**Finding 4: Resting invoice status shows `صالحة` (Valid) as if ETA approved it**
- Reality: Placeholder status from simulated API
- Fix: Show `تمت المحاكاة` (Simulated) or `قيد المعاينة` (Preview mode)

**Finding 5: Docstring in `eta_adapter.py` contradicts UI claims**
- Current docstring: "Simulates ETA submission" (correct)
- UI says: "Submit to ETA" (incorrect)
- Fix: Make UI match docstring intent

---

## Before you start

1. **Read `erp/einvoice/services/eta_adapter.py`** — confirm docstring + method behavior
2. **Read `erp/einvoice/services/eta_client.py`** — check if docstring or code makes false claims
3. **Read `apps/web/src/pages/einvoice/EInvoicesPage.tsx`** — see where action/status labels render
4. **Check `apps/web/src/i18n/locales/ar.json` + `en.json`** — search `einvoice.*` keys to find all copy

---

## Tasks

### Task 1: Reword module description in i18n (ar + en)

Find `einvoice.description` or similar in both locale files. Current (approximate):
- AR: `أرسال فواتيرك إلكترونيًا إلى مصلحة الضرائب المصرية`
- EN: `Send your invoices electronically to the Egyptian Tax Authority`

Replace with honest phrasing (choose one approach):
- **Option A (Preview):** "معاينة الفواتير للتقديم" / "Preview invoices for submission"
- **Option B (Simulate):** "محاكاة إرسال الفواتير" / "Simulate invoice submission"

Pick option A or B before editing. Recommend **Option B** (clearer that it's a simulation, not a preview that might confuse users into thinking it *will* submit later).

### Task 2: Reword action copy (ar + en)

Find all toast/button copy that says "إرسال" (submit) or "Send" in ETA context:
- Toast on successful "submission": `تم إرسال الفاتورة` → change to toast + action verb matching choice above
- Action button: `إرسال للمصلحة` → `محاكاة` or `معاينة`

Keep copy terse + brand-voice (calm, precise, trustworthy).

### Task 3: Relabel status column (ar + en)

In `EInvoicesPage.tsx` or the status enum:
- Column header: change from "معرّف المصلحة" (ETA ID) to "معرّف محلي" (Local ID)
- Status value: change from "صالحة" (Valid) to "تمت المحاكاة" (Simulated) or "قيد المعاينة" (Preview)

### Task 4: Update docstrings in backend

In `erp/einvoice/services/eta_adapter.py`:
- Docstring should say: "Simulates ETA submission for testing/preview. Does not submit to real ETA server."

In `erp/einvoice/services/eta_client.py` (if it has docstring/comments about real submission):
- Clarify: "Not currently wired into the issue() workflow. Real ETA submission requires integration decision."

---

## Smoke test

1. **Check i18n parity:** `node scripts/check-i18n-parity.mjs` — all keys must have ar + en
2. **Type check:** `npx tsc --noEmit` — no TS errors
3. **Live in browser:**
   - Log in as admin
   - Navigate to `/einvoice`
   - Verify module description is honest (no "submit to ETA" promise)
   - Check column headers + status labels
   - Reword action button/toast to match copy change
   - Test in Arabic RTL + English LTR, light + dark theme
4. **Brand feel:** Does the copy feel calm, precise, and trustworthy? No hype?

---

## Acceptance criteria

- ✅ All `einvoice.*` keys have both ar + en translations, none missing
- ✅ i18n parity check passes: `node scripts/check-i18n-parity.mjs`
- ✅ TypeScript clean: `npx tsc --noEmit`
- ✅ Live app shows honest copy (no false ETA submission promises)
- ✅ Module description + action + status labels all use consistent "simulate/preview" language
- ✅ Docstrings in `eta_adapter.py` + `eta_client.py` match reality
- ✅ Tested ar+en, light+dark

---

## Commit message

```
fix(einvoice): clarify that submission is simulated, not live ETA filing

- Reword module description from "submit to ETA" to "simulate submission"
- Update action button/toast copy to match (محاكاة / Simulate)
- Relabel status column from "معرّف المصلحة" to "معرّف محلي" (Local ID)
- Update backend docstrings to clarify eta_adapter is stub, eta_client not wired
- Fixes Standard 4 (Trust through transparency) — no false government filing claims

Closes brand-philosophy-review/SESSION_H P1 #1
```

---

## After this session

Once FILE_01 is done:
1. Rename this file to `FILE_01_EINVOICE_HONESTY_done.md`
2. Update `erp-status`: position = FILE_02 (Workflow UX)
3. Tell user: fresh session, start FILE_02 next
