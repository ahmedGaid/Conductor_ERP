# SESSION 8 — Dashboard & Reports
# Files: apps/mobile/lib/presentation/pages/home/**, lib/domain+data for dashboard/reports (new),
#        apps/mobile/lib/presentation/widgets/patterns/** (new)

**Objective:** the home tab — the same dashboard cards web shows (cash, receivables, approvals
waiting, recent activity — READ web's dashboard for the real list) and the reports library with
a mobile-honest viewer. This session also establishes the **module screen pattern** every later
module session reuses verbatim.

---

## Before You Start

1. Open web's dashboard page + its API module → exact cards, endpoints, refresh semantics.
2. Open web's reports pages → report list, parameters (period pickers, entity filters), output
   shapes (tables).
3. Open the session-04 `CachedRepository` — the stale-while-revalidate path is the ONLY data
   path for reads.
4. Recall `flutter-lessons` issues 4–6 (parallel loads, one emit; no reload flash; buildWhen).

"Do not write anything yet."

---

## Task A — The module screen pattern (`widgets/patterns/`) — build once, reuse in 09–13

1. `ListScreenPattern`: AppSearchField (debounced, server-side search param — same param web
   sends) + filter chips row (opens FilterSheet) + `ListView.builder` of `ListRow`s (stable keys,
   `prototypeItem` where rows are uniform) + pull-to-refresh (quiet spinner) + infinite scroll
   via the API's pagination shape + the three designed states. Saved default sort = web's
   default sort. Backed by a list bloc template: load = parallel fetches + ONE emit; mutations
   update in place (`flutter-lessons` 4–5).
2. `RecordScreenPattern`: header (title + StatusChip), sectioned fields (label/value rows,
   `number` variant for money via `core/money`), related-record links (deep-link navigation),
   actions in a bottom action bar or overflow AppSheet — populated per module later.
3. `FilterSheet` pattern: the mobile translation of web's filter bar — chips summarize active
   filters; sheet edits them; state serializes into the cache key.

## Task B — Dashboard (`pages/home/dashboard_page.dart`)

1. Cards mirror web: same order, same numbers, same i18n keys. Money via shared formatter;
   deltas coloured ONLY with word+arrow pairing (brand rule).
2. Each card deep-links into its module (receivables card → sales filtered list, approvals card
   → inbox tab).
3. Stale-while-revalidate: instant cached render, quiet refresh; `isStale` shows a subtle
   "آخر تحديث ..." caption — honesty without alarm.
4. Pull-to-refresh refreshes all dashboard queries together (one parallel load, one emit).

## Task C — Reports (`pages/home/reports/`)

1. Report list grouped as web groups them. Parameter screen per report: period picker (build
   `PeriodPicker` in patterns — month/quarter/year/custom, AppSheet-based, matching web's
   presets), entity selectors reusing FilterSheet.
2. Viewer: server returns the same table JSON web renders → mobile renders a virtualized,
   horizontally scrollable table (`ReportTable` pattern: two-axis scrolling with sticky first
   column, tabular numerics, RTL column order). Totals row pinned.
3. Share: export via the SAME server-side PDF/XLSX endpoints web uses (they exist — verify)
   → download to cache dir (`path_provider`) → OS share sheet (`share_plus`). NO client-side
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
- [ ] analyze + test + parity green; PARITY.md dashboard/reports rows flipped

## Risks

- Report tables are the hardest RTL surface — budget the session's slack here, not on cards.
- Dashboard endpoint shape drift by execution time → the Before-You-Start read decides truth.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_09_SALES.md
```
