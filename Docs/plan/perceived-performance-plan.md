# Perceived-Performance Plan — "Apple-smooth, not Android-choppy"

Status: **filed, not started.** Surfaced during linear-polish FILE_13 acceptance feel pass
(2026-07-06). One quick win already landed (font-swap reflow — see below); the rest is a dedicated
workstream for a fresh Opus session. This is NOT a bug list — it's a craft workstream about the
app *feeling* native and fluid.

## The complaint (verbatim intent)
The whole app feels laggy/rigid, not smooth. On load the top paints first, then the bottom follows
a moment later (like a brief network stall); elements shake/jump while loading. Interactions feel
rigid, not fluid — "an old C desktop program, not a modern native app." Bar to clear: **Linear /
Telegram / Apple-grade** motion and load calm.

Confirmed **not** dev-mode jank: symptoms are identical on the production build (`vite preview`).

## Already done (quick win, shipped in FILE_13 session)
- **Font-swap reflow killed.** Fonts were JS-imported via `@fontsource` with `font-display: swap`,
  so every page painted in a system fallback then swapped to IBM Plex Sans Arabic / Inter — Arabic
  metrics differ sharply, so the page reflowed mid-view ("text shakes"). Fix: self-hosted the six
  critical faces in `public/fonts/`, declared them in `src/styles/fonts.css` with
  `font-display: optional`, and `<link rel="preload">`ed the three at-first-paint faces in
  `index.html`. Result: brand font from first paint, zero swap reflow. User confirmed "much better."

## Remaining root causes → fixes (the workstream)

### 1. Eager shell + lazy content = "top paints, then bottom follows"
The top bar + sidebar render immediately; every routed page is `lazy()` behind a single
`<Suspense fallback={<ListSkeleton rows={6}/>}>` ([App.tsx:167](../../apps/web/src/App.tsx#L167)).
So the frame paints, then the body chunk + its data arrive and fill in below.
- Prefetch route chunks on hover/idle (the sidebar + command palette already know the routes).
- Consider a persistent shell with a content-area transition (fade/slide of ~120ms, decelerating)
  so the swap reads as intentional, not a stall.
- Warm the most-likely first route (Dashboard) so the landing paint is whole.

### 2. Skeleton ≠ final height = the "jump"
The generic `ListSkeleton rows={6}` fallback is one-size-fits-all; when real content of a different
height replaces it, the page reflows.
- Per-surface skeletons that reserve the **real** layout box (same paddings, same row heights,
  same column count) so content lands in place with no shift.
- Reserve above-the-fold heights for dashboard stat cards + "needs attention" panel.
- Audit for images/badges/number cells that arrive without a reserved box (CLS sources).

### 3. Motion audit — make every transition settled
- Sweep all `transition`/`animation` for properties that hit layout/paint (top/left/width/height)
  and move them to `transform`/`opacity` (compositor-only) — the difference between 60fps and jank.
- One motion scale (fast, decelerating, no bounce) applied consistently; honour reduced-motion.
- List/table row hover + selection, peek card, menus, toasts: confirm each animates on GPU props.
- Verify no long main-thread tasks on route change (React profiler): heavy synchronous work on
  mount stalls the paint and reads as lag.

### 4. Measure, don't guess
- Run Lighthouse + the Performance panel on the production build (`vite preview`) for real CLS /
  INP / long-task numbers before and after, per surface. Set a CLS budget (~0) and an INP budget.
- Consider adding a lightweight CLS/INP check to the perf gate so regressions are caught.

## Scope notes
- Zero new runtime dependencies without asking. Tokens/brand rules unchanged — this is motion +
  load craft, not a restyle.
- Break into session-sized files (e.g. FILE_01 route/shell transitions, FILE_02 per-surface
  skeletons, FILE_03 motion audit + measurement gate) when scheduled.
