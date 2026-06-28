# Conductor ERP — Brand Icon System

Production-ready icon package for **Conductor ERP**. Every asset is generated from a
single mathematically-defined vector mark (an open ring **C** + a three-bar swept
wing **E**) set on a **squircle (superellipse) tile** with continuous-curvature
corners — the same premium shape used by ChatGPT, Linear, Notion, Arc and modern
Apple app icons. Geometry and tile shape are **identical across favicon, desktop,
taskbar and mobile**. Flat, mono, no gradients/shadows/3D.

Each app-icon comes in **Light** (white tile, black mark) and **Dark** (black tile,
white mark) versions. The bare wordless mark (no tile) is also provided as the
`*-transparent.svg` files for in-product/inline use.

Extract this folder directly into:

```
apps/web/public/branding/
```

No post-processing required.

---

## Quick start (web `<head>`)

```html
<!-- Modern, auto light/dark, infinitely crisp -->
<link rel="icon" href="/branding/favicon.svg" type="image/svg+xml" />
<!-- Legacy + Windows fallback -->
<link rel="icon" href="/branding/favicon.ico" sizes="16x16 32x32 48x48" />
<!-- iOS home screen -->
<link rel="apple-touch-icon" sizes="180x180" href="/branding/apple-touch-icon.png" />
<!-- PWA + Android -->
<link rel="manifest" href="/branding/site.webmanifest" />
<!-- Windows tiles -->
<meta name="msapplication-config" content="/branding/browserconfig.xml" />
<meta name="theme-color" content="#000000" />
```

Using the mark in the UI (React/HTML):

```html
<img src="/branding/conductor-dark-transparent.svg" alt="Conductor" height="28" />   <!-- on light surfaces -->
<img src="/branding/conductor-light-transparent.svg" alt="Conductor" height="28" />  <!-- on dark surfaces -->
```

---

## Theme reference

| Variant                | Tile      | Mark      | Shape     |
|------------------------|-----------|-----------|-----------|
| Light app icon         | `#FFFFFF` | `#000000` | squircle  |
| Dark app icon          | `#000000` | `#FFFFFF` | squircle  |
| Bare mark (dark)       | none      | `#0A0A0A` | mark only |
| Bare mark (light)      | none      | `#FFFFFF` | mark only |

> `conductor-icon-light.svg` / `conductor-icon-dark.svg` are the canonical squircle
> app icons. `conductor-dark.svg` (white tile) and `conductor-light.svg` (black tile)
> are kept as aliases per the original brief naming.
> `favicon.svg` is a single adaptive squircle that flips light↔dark automatically via
> `prefers-color-scheme`; `favicon.ico` and the raster favicons ship as the dark tile
> so they read on any browser-tab color.

---

## What's inside

```
branding/
├── conductor-icon-light.svg        white squircle · black mark  (canonical)
├── conductor-icon-dark.svg         black squircle · white mark  (canonical)
├── conductor-dark.svg              = light squircle (alias)
├── conductor-light.svg             = dark squircle  (alias)
├── conductor-dark-transparent.svg  bare mark · black (no tile)
├── conductor-light-transparent.svg bare mark · white (no tile)
├── favicon.svg                     auto light/dark (prefers-color-scheme)
├── favicon.ico                     16 · 32 · 48
├── apple-touch-icon.png            180 (+152, +167 variants)
├── android-chrome-192/512.png      Chrome "any" icons
├── icon-16…512.png                 flat transparent set (general use)
│
├── icons/
│   ├── light/   icon-16…512.png    white bg · black mark
│   ├── dark/    icon-16…512.png    black bg · white mark
│   ├── transparent-black/          transparent · black mark
│   └── transparent-white/          transparent · white mark
│
├── favicon/     favicon-16/32/48.png
│
├── ios/         AppStore-1024.png · AppIcon-180/167/152/120/76.png
│
├── android/     maskable-192/512 · monochrome-192/512
│                adaptive-foreground · adaptive-background · play-store-512
│
├── pwa/         icon-192/512 · maskable-192/512 · monochrome-192/512
│
├── desktop/
│   ├── windows.ico                 16·32·48·64·128·256
│   ├── conductor.icns              16→1024 (macOS, squircle)
│   ├── linux/    64·128·256·512.png
│   ├── taskbar/  windows-light/dark.png
│   └── dock/     macos-light/dark.png
│
├── manifest.json · site.webmanifest · browserconfig.xml
└── README.md
```

### iOS
Full-bleed **square, fully opaque** (no alpha) per Apple HIG — iOS itself applies the
squircle mask on the home screen, so these must not be pre-rounded. `AppStore-1024.png`
is the App Store listing asset; `AppIcon-*` cover iPhone (120/180) and iPad (76/152/167).
`*-dark.png` are the iOS 17+ dark-appearance variants (black tile, white mark).

### Android
- **adaptive-foreground / adaptive-background** — drop into
  `res/mipmap-anydpi-v26/`. Mark sits inside the 66% safe circle.
- **maskable-*** — `purpose: "maskable"` in the manifest.
- **monochrome-*** — `purpose: "monochrome"` for Android 13+ themed icons.
- **play-store-512.png** — Play Console listing.

### Desktop
- **windows.ico** — multi-resolution app icon (white tile, black mark).
- **conductor.icns** — macOS bundle icon (`Contents/Resources/`), rendered as the
  Big-Sur squircle.
- **linux/** — hicolor PNG set (`/usr/share/icons/hicolor/<size>/apps/`).
- **taskbar/ & dock/** — optimized light/dark silhouettes for pinned bars.

---

## Regenerating

All assets derive from one parametric source of truth (`geo.js`): an open ring of
outer-radius 200 / stroke 50 with a 60° right opening, plus three sheared
parallelogram bars (length 174, thickness 42, gap 28, shear 0.60, corner-radius 9).
Adjust those constants and re-export to rescale the entire system while keeping
every format pixel-identical.

© Conductor ERP. All rights reserved.
