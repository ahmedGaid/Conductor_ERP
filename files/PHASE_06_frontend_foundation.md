# Phase 06 — Frontend Foundation (Design System + i18n + RTL)

## Goal
Stand up the React app with the design tokens, Tailwind/shadcn theme, the app shell (sidebar, top command bar),
fonts, and a complete i18n layer that defaults to **Arabic / RTL**, switches live to English / LTR, and **fails the
build on any missing translation key**. No screen content yet — just a correct, mirror-able shell.

## Files to touch
```
apps/web/
├── index.html                  # <html lang dir> set at runtime
├── vite.config.ts
├── tailwind.config.ts          # design tokens as theme extension
├── postcss.config.js
├── src/
│   ├── main.tsx
│   ├── app/AppShell.tsx         # sidebar + topbar + content slot
│   ├── app/Sidebar.tsx          # icon+label nav; logical-inline-start
│   ├── app/CommandBar.tsx       # global search w/ ⌘K affordance
│   ├── app/LanguageSwitcher.tsx # toggles ar↔en + dir live
│   ├── theme/tokens.css         # CSS custom properties (single source of truth)
│   ├── i18n/index.ts            # i18next config, ar default + fallback
│   ├── i18n/ar.json
│   ├── i18n/en.json
│   ├── lib/format.ts            # Intl.NumberFormat / DateTimeFormat per locale
│   ├── components/ui/*          # shadcn primitives (button, card, table, badge/Pill, input)
│   └── components/StatusPill.tsx
└── scripts/check-i18n-parity.ts # build gate: ar/en key sets must be identical
```

## Design tokens (`theme/tokens.css`) — define once, reference everywhere; NO hardcoded hex in components
```css
:root{
  --app-bg:#FAFAFA; --surface:#FFFFFF; --text-primary:#0A0A0A; --text-muted:#6B6B6B;
  --accent:#1B4F8A;                 /* single primary-action accent */
  --ok:#16A34A; --info:#2563EB; --warn:#D97706; --err:#DC2626; --neutral:#6B6B6B;
  --ok-bg:#E8F5EE; --info-bg:#E8EEFB; --warn-bg:#FBF1E3; --err-bg:#FBEAEA; --neutral-bg:#F0F0F0;
  --hairline:#EDEDED;
  --radius-card:12px; --radius-control:8px;
  --space-card:22px;                /* 20–24px generous card padding */
  --shadow-card:0 1px 2px rgba(10,10,10,.05);  /* at most one soft shadow; flat */
  --font-ar:"IBM Plex Sans Arabic"; --font-latin:"Inter";
}
```
Tailwind theme maps these (`colors.surface`, `borderRadius.card`, etc.). Weights limited to **400 / 500**.
Sentence case everywhere. No gradients/glow/neon.

## i18n + RTL (mandatory behaviors)
- `i18next` init: `lng:'ar'`, `fallbackLng:'ar'`, resources `{ ar, en }`. **No hardcoded UI strings** anywhere —
  every label/placeholder/status/toast goes through `t()`.
- On language change, set `document.documentElement.lang` and `dir` (`ar→rtl`, `en→ltr`) live, no reload.
- **Logical CSS only**: `margin-inline-start/end`, `padding-inline-*`, `inset-inline-start`, `text-align:start`.
  Never physical `left/right` for anything that must mirror. Sidebar sits on the **inline-start** side (right in RTL).
- Numerals/dates via `Intl` with the active locale; default Arabic locale presentation; never hardcode `en-US`.
- Fonts: bundle IBM Plex Sans Arabic (full diacritics) + Inter; Arabic must never fall back to a Latin-only font.
  Wrap embedded LTR tokens (IDs like `SO-000123`) with bidi isolation (`<bdi>` / `unicode-bidi:isolate`) to prevent direction bleed.

## App shell
- Fixed ~240px sidebar (inline-start) with the reference nav items (Home, Accounting, HR & Payroll, CRM, Sales,
  Purchasing, Inventory, Manufacturing, Projects, Assets, Reports, Settings) using one outline icon set (Lucide).
- Persistent full-width top command bar: search input with `⌘K` affordance; placeholder
  `"ابحث أو اكتب أمراً…"` (ar) / `"Search or type a command…"` (en) via `t()`.
- Language switcher in the top bar.

## Translation completeness build gate (`scripts/check-i18n-parity.ts`)
- Load `ar.json` + `en.json`, flatten keys, assert the key sets are **identical** (symmetric difference empty).
- Wire into `apps/web` `build` script as a pre-step so `npm -w apps/web run build` FAILS on any missing/extra key.

## Verification (gate:06)
- [ ] `npm -w apps/web run build` succeeds; removing one key from `en.json` makes it FAIL (gate proves both directions).
- [ ] App boots with `<html lang="ar" dir="rtl">`; sidebar renders on the right.
- [ ] Language switcher flips to `en`/`ltr` live (no reload); sidebar moves to the left; no clipped/overflowing text.
- [ ] grep gate: no raw hex colors in `src/components`/`src/app` except `tokens.css` (everything else uses CSS vars/Tailwind tokens).
- [ ] grep gate: no physical `left:`/`right:` in mirror-relevant styles (use logical properties).

## Done signal
A bilingual, RTL-default shell renders correctly in both directions with a token-driven theme and a build that
breaks on missing translations. `gate:06` is green.
