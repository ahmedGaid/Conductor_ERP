# Conductor ERP — Brand Icon System

Production-ready icon package for **Conductor ERP**. Every asset is generated from a
single mathematically-defined vector mark (an open ring **C** + a three-bar swept
wing **E**), so geometry is **identical across every format and size**. Flat, mono,
no gradients/shadows/3D — built to sit comfortably beside ChatGPT, Notion, Linear,
Stripe, Vercel and Cursor.

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

| Variant            | Background | Mark    |
|--------------------|------------|---------|
| Light mode         | `#FFFFFF`  | `#000000` |
| Dark mode          | `#000000`  | `#FFFFFF` |
| Transparent (dark) | none       | `#0A0A0A` |
| Transparent (light)| none       | `#FFFFFF` |

> Naming note: per the brief, `conductor-dark.svg` = **black mark on white**,
> `conductor-light.svg` = **white mark on black**.

---

## What's inside

```
branding/
├── conductor-dark.svg              white bg · black mark   (master)
├── conductor-light.svg             black bg · white mark   (master)
├── conductor-dark-transparent.svg  transparent · black mark
├── conductor-light-transparent.svg transparent · white mark
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
Square, fully opaque (no alpha) per Apple HIG — the system applies the rounded
mask. `AppStore-1024.png` is the App Store listing asset; `AppIcon-*` cover
iPhone (120/180) and iPad (76/152/167).

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
