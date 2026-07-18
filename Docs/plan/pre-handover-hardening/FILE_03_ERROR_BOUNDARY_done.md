# FILE_03 — Top-level React error boundary  🟠 High

## The finding
Grep across `apps/web/src` for `ErrorBoundary` / `componentDidCatch` /
`getDerivedStateFromError` returns **zero matches**. Any uncaught render error white-screens the
entire app with no recovery — a blank screen for the customer. This also breaks the project's own
rule that every error state is designed (Conductor Standard 7; Directive).

## Before you start (read)
- `apps/web/src/App.tsx` (where the shell + router mount)
- `apps/web/src/styles/tokens.css` (colours/spacing to reuse — tokens only, no raw hex)
- An existing designed empty/error state (e.g. the UX-states batch from twenty-harvest FILE_16) for
  visual + copy consistency
- `conductor-brand` skill — brand-feel checklist for the fallback copy/visual

## Tasks
- [ ] Add `apps/web/src/components/AppErrorBoundary.tsx` — a class component with
      `getDerivedStateFromError` + `componentDidCatch` (log to console; no external service unless
      one already exists).
- [ ] Designed fallback state: monochrome, centered, one calm line + a "reload" primary action.
      Bilingual — both strings are keys in `ar.json` AND `en.json` (parity is build-blocking).
- [ ] Wrap the app shell / routed area in `App.tsx` with the boundary (inside the i18n + theme
      providers so the fallback is localized and themed).
- [ ] Reset-on-navigate: allow recovery without a full reload where cheap (optional; reload button
      is the floor).

## Watch
- Fallback must read identically calm in RTL and LTR — logical CSS only, no physical left/right.
- Copy is blame-free and human ("حدث خطأ ما — أعد تحميل الصفحة" / "Something went wrong — reload"),
  never a stack trace or error code to the user.
- Reuse existing button/icon primitives; no new dependency, no imported icon library.

## Done when
Forcing a render error (temporarily throw in a page component) shows the designed bilingual fallback
in both `ar` and `en`, not a white screen; removing the throw restores normal render. Gates green.

## How to test
- Temporarily add `throw new Error('boom')` to a page body → app shows the designed fallback, reload
  button works. Remove the throw.
- Toggle locale → fallback text switches ar/en. Toggle theme → fallback respects it.
- `node scripts/check-i18n-parity.mjs` + `npx tsc -b` + `python scripts/gates/gate03.py` green.
- Run the `conductor-brand` brand-feel checklist on the fallback.
