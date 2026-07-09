# SESSION 8 — Dashboard & Reports
# Files: apps/mobile/app/(tabs)/home/**, apps/mobile/src/api/endpoints/dashboard.ts,
#        reports.ts (new), apps/mobile/src/ui/patterns/** (new)

**Objective:** the home tab — the same dashboard cards web shows (cash, receivables, approvals
waiting, recent activity — READ web's dashboard for the real list) and the reports library with
a mobile-honest viewer. This session also establishes the **module screen pattern** every later
module session reuses verbatim.

---

## Before You Start

1. Open web's dashboard page + its API module → exact cards, endpoints, refresh semantics.
2. Open web's reports pages → report list, parameters (period pickers, entity filters), output
   shapes (tables).
3. Open `src/offline/readCache.ts` → `useApiQuery` is the ONLY data path for reads.

"Do not write anything yet."

---

## Task A — The module screen pattern (`src/ui/patterns/`) — build once, reuse in 09–13

1. `ListScreen` pattern: SearchField (debounced, server-side search param — same param web
   sends) + filter chips row (opens filter Sheet) + `FlashList` of `ListRow`s + pull-to-refresh
   (quiet spinner) + infinite scroll via the API's pagination shape + the three designed states.
   Saved default sort = web's default sort.
2. `RecordScreen` pattern: header (title + StatusChip), sectioned fields (label/value rows,
   `number` variant for money via `packages/core/money`), related-record links (deep-link
   navigation), actions in a bottom action bar or overflow Sheet — populated per module later.
3. `FilterSheet` pattern: the mobile translation of web's filter bar — chips summarize active
   filters; sheet edits them; state serializes into the cache key.

## Task B — Dashboard (`home/index.tsx`)

1. Cards mirror web: same order, same numbers, same i18n keys. Money via shared formatter;
   deltas coloured ONLY with word+arrow pairing (brand rule).
2. Each card deep-links into its module (receivables card → sales filtered list, approvals card
   → inbox tab).
3. Stale-while-revalidate: instant cached render, quiet refresh; `isStale` beyond TTL shows a
   subtle "آخر تحديث ..." caption — honesty without alarm.
4. Pull-to-refresh refreshes all dashboard queries together.

## Task C — Reports (`home/reports/`)

1. Report list grouped as web groups them. Parameter screen per report: period picker (build
   `PeriodPicker` in patterns — month/quarter/year/custom, Sheet-based, matching web's presets),
   entity selectors reusing FilterSheet.
2. Viewer: server returns the same table JSON web renders → mobile renders a virtualized,
   horizontally scrollable table (`ReportTable` pattern: sticky first column, tabular numerics,
   RTL column order). Totals row pinned.
3. Share: export via the SAME server-side PDF/XLSX endpoints web uses (they exist — verify)
   → download to cache dir → OS share sheet (`expo-file-system` + `Sharing` — check current API;
   `expo-sharing` may need adding to the approved list via DECISIONS one-liner). NO client-side
   PDF generation — documents render server-side, identically for every surface.

---

## Smoke Test

- [ ] Dashboard matches web side-by-side for the same company: same cards, same values, same
      Arabic terms; numbers tabular-aligned
- [ ] Airplane mode cold open → cached dashboard + stale caption; online → silent refresh
- [ ] Card tap → correct filtered module stub/list
- [ ] Run one real report ar + en: parameters round-trip, table scrolls both axes, first column
      sticky, totals pinned, RTL column order correct
- [ ] Export → share sheet delivers the same PDF web produces
- [ ] Tablet: dashboard uses the wide grid; report table uses the width
- [ ] tsc + parity green; PARITY.md dashboard/reports rows flipped

## Risks

- Report tables are the hardest RTL surface — budget the session's slack here, not on cards.
- Dashboard endpoint shape drift by execution time → the Before-You-Start read decides truth.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_09_SALES.md
```
