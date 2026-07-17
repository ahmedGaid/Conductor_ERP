# Field primitives rollout — INDEX

**Added 2026-07-17.** Harvested from the Twenty comparison: two new field primitives are built and
proven on one screen each. This plan fans them out to the whole app so every long list and every
date field feels the same.

The primitives (already in `apps/web/src/components/`, do NOT rebuild):
- **`ComboBox`** — searchable single-select. Trigger looks like a `<select>` (shared
  `.combobox-trigger` styling in `global.css`); opens a `Popover` with a search box + checkmarked,
  filtered list. Emits/consumes the option `value` (a code), same contract as the native `<select>`
  it replaces. Proven on `pages/sales/NewOrderPage.tsx` (Customer / Warehouse / line Item).
- **`DatePicker`** — calendar field on our tokens/icons (no new dep; Twenty uses react-datepicker +
  IMask, we do not). Trigger looks like a field with a calendar glyph; opens a `Popover` calendar:
  Month + Year `ComboBox`es, prev/next steppers, day grid, Today / Clear. ISO `YYYY-MM-DD` on the
  wire, Latin digits both locales, localized month/weekday names, RTL-correct (Saturday-start +
  mirrored nav in Arabic). Proven on `pages/accounting/JournalEntryPage.tsx` (entry date).

| File | Scope | Model |
|---|---|---|
| FILE_01 ✅ **DONE (2026-07-17)** | Fanned `ComboBox` to every long/dynamic entry `<select>`; fanned `DatePicker` to every `type="date"` in the app. Report-page "All"-default filters + select-as-action controls intentionally deferred (see FILE_01 Deferred). | Sonnet (mechanical, clear pattern) |

Model note: mechanical fan-out against a settled pattern — **Sonnet fits** (Haiku if the sweeps stay
copy-shaped). Say so and let the user `/model` before spending Opus.
