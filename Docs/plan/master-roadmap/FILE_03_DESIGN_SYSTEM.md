# D3 — Design System & UX

> The brand triad (`Docs/Brand/`) owns the rules; `conductor-brand` + `erp-frontend` skills
> own the discipline; `unified-ui-plan` (queue 4) + `linear-polish-plan` (queue 3) own the
> in-flight surface work. **Do not duplicate any of those.** This domain adds what none of
> them contain: a browsable component catalog, accessibility floor, and mechanical drift
> gates that make weaker agents safe on UI.

---

## Phase D3.P1 — Catalog & drift gates

### D3.P1.T1 — Component catalog page (internal)
**Status:** todo · **Model:** Sonnet
**Objective:** a dev-only route `/dev/catalog` rendering every shared primitive (buttons, inputs, selects, toasts, empty/error/loading states, table kit, meta columns, header bar) in both languages, both themes, with the token names used.
**Rationale:** agents reuse primitives only when they can SEE the inventory; also the visual-review surface for D3.P1.T3. No Storybook — no new dependency.
**Prerequisites:** unified-ui FILE_07 (meta primitives) done — it is (`_done` suffix).
**Steps:**
1. Inventory shared components under `apps/web/src/components/` via codegraph; group by kind.
2. `apps/web/src/pages/dev/CatalogPage.tsx` + route guarded by `import.meta.env.DEV`.
3. Each entry: rendered sample(s), component name, source path, token vars it consumes.
4. AR/EN toggle + light/dark toggle inline (reuse existing theme/i18n switches).
**Architecture decisions:** dev-only (excluded from prod bundle via env guard); catalog is generated from an explicit registry array, not filesystem magic.
**Affected files:** `apps/web/src/pages/dev/CatalogPage.tsx` (new), registry file, `apps/web/src/App.tsx` (route), locales (dev strings may stay EN — mark exempt per parity script rules if supported, else add both).
**Acceptance criteria:** every component listed in the registry renders in 4 combos (ar/en × light/dark) without console errors; missing-from-catalog primitives ticketed.
**Testing:** `npx tsc --noEmit`, parity script, manual sweep of the 4 combos.
**DoD:** gates + brand-feel checklist, status flipped.

### D3.P1.T2 — Token & logical-CSS drift gate hardening
**Status:** todo · **Model:** Haiku
**Objective:** extend `scripts/gates/gate03.py` (or add gate16) to also fail on: physical CSS properties (`left:`, `right:`, `margin-left`, etc.) outside sanctioned files, raw px font sizes outside tokens, hex colors in TSX inline styles.
**Rationale:** current gate catches most; the remaining leak paths are exactly what weak models emit.
**Prerequisites:** read `scripts/gates/gate03.py` first — extend, don't fork rules already there.
**Steps:** 1. Add the three checks with an allowlist file. 2. Seed allowlist from current violations; file follow-up fix tasks if any are real. 3. Register.
**Architecture decisions:** same shrink-only allowlist pattern as gate15.
**Affected files:** `scripts/gates/gate03.py` or `gate16.py` (new), allowlist, `_run.py`.
**Acceptance criteria:** gate green on tree; planted violation of each class fails with file:line.
**Testing:** run gate before/after planted violations.
**DoD:** gates green, status flipped.

## Phase D3.P2 — Accessibility floor

### D3.P2.T1 — Keyboard & focus audit (app shell + top 5 pages)
**Status:** todo · **Model:** Sonnet
**Objective:** every interactive element reachable and operable by keyboard, visible focus ring from tokens, focus trapped in dialogs and returned on close, on shell + sales orders, invoice detail, inventory list, settings, assistant panel.
**Rationale:** Linear bar includes keyboard-first; linear-polish added shortcuts — this task makes the base layer sound. Also pre-work for any public-sector customer.
**Prerequisites:** linear-polish plan done (queue 3).
**Steps:** 1. Manual tab-order sweep per page, both directions (RTL!). 2. Fix: `tabIndex`, focus ring token (`--focus-ring` — add to tokens.css if missing), dialog trap util in `apps/web/src/components/` if absent. 3. Document keyboard map in help page.
**Architecture decisions:** one focus-ring token; no `outline: none` without replacement (add to gate16 allowlist checks later).
**Affected files:** shell components, dialog primitive, `apps/web/src/styles/tokens.css`, touched pages, help content, locales.
**Acceptance criteria:** full keyboard journey on the 5 pages without a mouse, both languages; escape/close returns focus to the opener.
**Testing:** manual scripted sweep (write the script into the task PR description); tsc + parity + gates.
**DoD:** gates + checklist, status flipped.

### D3.P2.T2 — Contrast + reduced-motion verification
**Status:** todo · **Model:** Haiku
**Objective:** script `apps/web/scripts/check-contrast.mjs` computing WCAG AA contrast for every token pair used as fg/bg combos declared in a manifest; verify `prefers-reduced-motion` honored by the motion tokens.
**Rationale:** mechanical proof the palette meets AA in both themes; motion rule is already brand law — verify it.
**Prerequisites:** D3.P1.T2.
**Steps:** 1. Manifest of fg/bg pairs (start: text/surface, muted/surface, primary/on-primary per theme). 2. Script parses `tokens.css`, computes ratios, fails <4.5 (3.0 for large-text pairs flagged in manifest). 3. Grep-check all `transition/animation` declarations sit behind the motion tokens/reduced-motion guard. 4. Register in gate runner.
**Architecture decisions:** manifest explicit, not inferred.
**Affected files:** `apps/web/scripts/check-contrast.mjs` (new), manifest JSON, `_run.py` or package script.
**Acceptance criteria:** script green both themes; deliberately lowered token fails.
**Testing:** run script; plant failure; restore.
**DoD:** gates green, status flipped.

## Phase D3.P3 — UX debt sweeps (recurring)

### D3.P3.T1 — Designed-states census
**Status:** todo · **Model:** Sonnet
**Objective:** enumerate every page's empty/error/loading state; each is designed (illustration/wording per brand) or gets a fix commit; census table committed to `Docs/plan/master-roadmap/ux-census.md`.
**Rationale:** "never bare No data" is law but unaudited fleet-wide.
**Prerequisites:** D3.P1.T1 (catalog shows the canonical states).
**Steps:** 1. Route inventory from `App.tsx`. 2. Per route: force the 3 states (dev tools/network block), record verdict. 3. Fix failures using the shared state components; one commit per app area.
**Architecture decisions:** reuse the canonical state components only.
**Affected files:** census doc (new), offending pages, locales.
**Acceptance criteria:** census 100% rows verdict `ok`; zero bare states.
**Testing:** gates + parity; spot manual re-check.
**DoD:** gates + checklist, census committed, status flipped.
