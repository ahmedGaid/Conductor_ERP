# Phase 1 — CSS Token Schema
# ZERO RISK — New files only. Nothing existing is modified.

---

## What you will do in this phase

1. Create `src/styles/modules/_module-tokens.css` — all module accent tokens
2. Create `src/styles/modules/_status-tokens.css` — status/semantic tokens (separate namespace)
3. Create `src/styles/modules/_dark-mode-tokens.css` — dark mode overrides
4. Import all three into `src/styles/globals.css` (append only — do not change anything above)

---

## Step 1 — Create `src/styles/modules/_module-tokens.css`

Create the directory `src/styles/modules/` if it does not exist.

```css
/* ============================================================
   CONDUCTOR ERP — MODULE ACCENT TOKENS
   Rules:
   - Every accent has a -light and -dark variant
   - Light: desaturated, soft tint for badges and accent bars
   - Dark: +15% lightness, same saturation — for dark mode surfaces
   - Tint: very low opacity version for badge backgrounds
   - Text: darkened version of accent for text on tinted backgrounds
   - NEVER use these on button elements (use --color-action-primary only)
   ============================================================ */

:root {
  /* ── SALES (Soft Blue) ──────────────────────────── */
  --module-sales-accent-light:      #A7C7E7;
  --module-sales-accent-dark:       #6B9BD1;
  --module-sales-tint-light:        rgba(167, 199, 231, 0.15);
  --module-sales-tint-dark:         rgba(107, 155, 209, 0.18);
  --module-sales-text-light:        #1D4A7A;
  --module-sales-text-dark:         #B8D4EE;
  --module-sales-bar:               var(--module-sales-accent-light);

  /* ── PURCHASING (Sage Green) ────────────────────── */
  --module-purchasing-accent-light: #A8C5A0;
  --module-purchasing-accent-dark:  #72A869;
  --module-purchasing-tint-light:   rgba(168, 197, 160, 0.15);
  --module-purchasing-tint-dark:    rgba(114, 168, 105, 0.18);
  --module-purchasing-text-light:   #2A5C24;
  --module-purchasing-text-dark:    #BACED6;
  --module-purchasing-bar:          var(--module-purchasing-accent-light);

  /* ── INVENTORY (Muted Orange) ───────────────────── */
  --module-inventory-accent-light:  #E8C49A;
  --module-inventory-accent-dark:   #D4964E;
  --module-inventory-tint-light:    rgba(232, 196, 154, 0.15);
  --module-inventory-tint-dark:     rgba(212, 150, 78, 0.18);
  --module-inventory-text-light:    #7A4A10;
  --module-inventory-text-dark:     #F0D5B0;
  --module-inventory-bar:           var(--module-inventory-accent-light);

  /* ── ACCOUNTING (Pastel Purple) ─────────────────── */
  --module-accounting-accent-light: #C3B4E8;
  --module-accounting-accent-dark:  #9B85D4;
  --module-accounting-tint-light:   rgba(195, 180, 232, 0.15);
  --module-accounting-tint-dark:    rgba(155, 133, 212, 0.18);
  --module-accounting-text-light:   #4A2D8C;
  --module-accounting-text-dark:    #D8CCF2;
  --module-accounting-bar:          var(--module-accounting-accent-light);

  /* ── MANUFACTURING (Warm Slate — NOT red) ───────── */
  /* NOTE: Red is reserved for status-error only.
     Manufacturing uses warm slate/terracotta instead. */
  --module-manufacturing-accent-light: #C4A99A;
  --module-manufacturing-accent-dark:  #A87D6B;
  --module-manufacturing-tint-light:   rgba(196, 169, 154, 0.15);
  --module-manufacturing-tint-dark:    rgba(168, 125, 107, 0.18);
  --module-manufacturing-text-light:   #6B3320;
  --module-manufacturing-text-dark:    #DEC4B8;
  --module-manufacturing-bar:          var(--module-manufacturing-accent-light);

  /* ── CRM (Indigo) ───────────────────────────────── */
  --module-crm-accent-light:        #9BAED4;
  --module-crm-accent-dark:         #6680BC;
  --module-crm-tint-light:          rgba(155, 174, 212, 0.15);
  --module-crm-tint-dark:           rgba(102, 128, 188, 0.18);
  --module-crm-text-light:          #1E3670;
  --module-crm-text-dark:           #B8C6E8;
  --module-crm-bar:                 var(--module-crm-accent-light);

  /* ── HR (Teal) ──────────────────────────────────── */
  /* NOTE: HR teal is deliberately shifted toward blue-teal
     to stay discriminable from Purchasing sage-green under CVD. */
  --module-hr-accent-light:         #8EC4C4;
  --module-hr-accent-dark:          #56A0A0;
  --module-hr-tint-light:           rgba(142, 196, 196, 0.15);
  --module-hr-tint-dark:            rgba(86, 160, 160, 0.18);
  --module-hr-text-light:           #1A5C5C;
  --module-hr-text-dark:            #B0DCDC;
  --module-hr-bar:                  var(--module-hr-accent-light);

  /* ── GLOBAL ACTION BUTTONS (never override per-module) ── */
  --color-action-primary:           #1A1A1A;
  --color-action-primary-hover:     #333333;
  --color-action-primary-text:      #FFFFFF;
}
```

---

## Step 2 — Create `src/styles/modules/_status-tokens.css`

```css
/* ============================================================
   CONDUCTOR ERP — STATUS / SEMANTIC TOKENS
   SEPARATE NAMESPACE from module accents.

   Rules:
   - Hues are deliberately offset from module accents
   - status-error uses crimson (NOT brick red like old Manufacturing)
   - status-success uses a deeper, more saturated green than Purchasing sage
   - status-warning uses amber — no module uses amber
   - These tokens apply to: status tags, void indicators, error states,
     form validation, notification banners
   - These tokens NEVER apply to: module badges, accent bars, nav items
   ============================================================ */

:root {
  /* ── ERROR (Crimson — offset from any module red) ── */
  --color-status-error-bg:        rgba(220, 38, 38, 0.1);
  --color-status-error-border:    rgba(220, 38, 38, 0.3);
  --color-status-error-text:      #991B1B;
  --color-status-error-text-dark: #FCA5A5;

  /* ── SUCCESS (Deep Green — more saturated than Purchasing) ── */
  --color-status-success-bg:        rgba(22, 163, 74, 0.1);
  --color-status-success-border:    rgba(22, 163, 74, 0.3);
  --color-status-success-text:      #166534;
  --color-status-success-text-dark: #86EFAC;

  /* ── WARNING (Amber — no module uses this hue) ── */
  --color-status-warning-bg:        rgba(217, 119, 6, 0.1);
  --color-status-warning-border:    rgba(217, 119, 6, 0.3);
  --color-status-warning-text:      #92400E;
  --color-status-warning-text-dark: #FCD34D;

  /* ── DRAFT / PENDING (Neutral) ── */
  --color-status-draft-bg:          rgba(107, 114, 128, 0.1);
  --color-status-draft-border:      rgba(107, 114, 128, 0.3);
  --color-status-draft-text:        #374151;
  --color-status-draft-text-dark:   #D1D5DB;

  /* ── VOID / REVERSED (Deep Crimson — distinct from error) ── */
  --color-status-void-bg:           rgba(153, 27, 27, 0.08);
  --color-status-void-border:       rgba(153, 27, 27, 0.25);
  --color-status-void-text:         #7F1D1D;
  --color-status-void-text-dark:    #FCA5A5;

  /* ── REVERSAL ICON INDICATOR ── */
  /* Used on reverse transactions (returns, credit notes).
     Applied to badge icon only — NOT to the full screen color. */
  --color-reversal-indicator:       var(--color-status-void-text);
}
```

---

## Step 3 — Create `src/styles/modules/_dark-mode-tokens.css`

```css
/* ============================================================
   CONDUCTOR ERP — DARK MODE OVERRIDES
   Applied when [data-theme="dark"] or prefers-color-scheme: dark.

   Rule: Raise lightness +15% from light variant.
         Keep saturation identical — do NOT increase saturation.
         Module accents must remain desaturated on dark surfaces.
   ============================================================ */

@media (prefers-color-scheme: dark) {
  :root {
    --module-sales-bar:           var(--module-sales-accent-dark);
    --module-purchasing-bar:      var(--module-purchasing-accent-dark);
    --module-inventory-bar:       var(--module-inventory-accent-dark);
    --module-accounting-bar:      var(--module-accounting-accent-dark);
    --module-manufacturing-bar:   var(--module-manufacturing-accent-dark);
    --module-crm-bar:             var(--module-crm-accent-dark);
    --module-hr-bar:              var(--module-hr-accent-dark);

    --color-status-error-text:    var(--color-status-error-text-dark);
    --color-status-success-text:  var(--color-status-success-text-dark);
    --color-status-warning-text:  var(--color-status-warning-text-dark);
    --color-status-draft-text:    var(--color-status-draft-text-dark);
    --color-status-void-text:     var(--color-status-void-text-dark);

    --color-action-primary:       #F5F5F5;
    --color-action-primary-hover: #DEDEDE;
    --color-action-primary-text:  #0A0A0A;
  }
}

/* Also support explicit data attribute override for theme toggle */
[data-theme="dark"] {
  --module-sales-bar:           var(--module-sales-accent-dark);
  --module-purchasing-bar:      var(--module-purchasing-accent-dark);
  --module-inventory-bar:       var(--module-inventory-accent-dark);
  --module-accounting-bar:      var(--module-accounting-accent-dark);
  --module-manufacturing-bar:   var(--module-manufacturing-accent-dark);
  --module-crm-bar:             var(--module-crm-accent-dark);
  --module-hr-bar:              var(--module-hr-accent-dark);

  --color-status-error-text:    var(--color-status-error-text-dark);
  --color-status-success-text:  var(--color-status-success-text-dark);
  --color-status-warning-text:  var(--color-status-warning-text-dark);
  --color-status-draft-text:    var(--color-status-draft-text-dark);
  --color-status-void-text:     var(--color-status-void-text-dark);

  --color-action-primary:       #F5F5F5;
  --color-action-primary-hover: #DEDEDE;
  --color-action-primary-text:  #0A0A0A;
}
```

---

## Step 4 — Append imports to `src/styles/globals.css`

Open `src/styles/globals.css` and **append** these 3 lines at the very end.
Do not change anything that already exists in the file:

```css
/* Conductor ERP — Module Identity System */
@import './modules/_module-tokens.css';
@import './modules/_status-tokens.css';
@import './modules/_dark-mode-tokens.css';
```

---

## Step 5 — Create the token linter script

Create `scripts/design-check.js`:

```javascript
// Conductor ERP — Design Token Linter
// Checks that no hardcoded hex colors exist in component files.
// Run: node scripts/design-check.js

const fs = require('fs');
const path = require('path');
const glob = require('glob'); // install if needed: npm i -D glob

const FORBIDDEN = [
  /#[0-9a-fA-F]{6}/g,     // 6-digit hex
  /#[0-9a-fA-F]{3}/g,     // 3-digit hex
  /color:\s*red/g,
  /color:\s*green/g,
  /color:\s*blue/g,
  /background:\s*#/g,
];

const SCAN_DIRS = ['src/components', 'src/modules', 'src/pages'];
const ALLOWED_FILES = ['_module-tokens.css', '_status-tokens.css', '_dark-mode-tokens.css'];

let violations = 0;

SCAN_DIRS.forEach(dir => {
  const files = glob.sync(`${dir}/**/*.{css,scss,jsx,tsx,vue}`);
  files.forEach(file => {
    if (ALLOWED_FILES.some(f => file.endsWith(f))) return;
    const content = fs.readFileSync(file, 'utf8');
    FORBIDDEN.forEach(pattern => {
      const matches = content.match(pattern);
      if (matches) {
        console.error(`[VIOLATION] ${file} — hardcoded color: ${matches[0]}`);
        violations++;
      }
    });
  });
});

if (violations === 0) {
  console.log('[PASS] No hardcoded colors found in component files.');
} else {
  console.error(`[FAIL] ${violations} violation(s) found. Fix before continuing.`);
  process.exit(1);
}
```

---

## Verification for Phase 1

```bash
# 1. Confirm token files exist
ls src/styles/modules/

# 2. Confirm imports were appended (must show 3 import lines at end)
tail -5 src/styles/globals.css

# 3. Run design check (should PASS — no existing components have hardcoded colors yet)
node scripts/design-check.js

# 4. Start app — must still work with zero errors
npm run dev
```

All 4 must pass. If the app throws an import error, check that the globals.css path
matches your actual file structure.

---

## What you just built

```
src/styles/modules/
  _module-tokens.css       ← 7 module accents, light+dark pairs, tints, text colors
  _status-tokens.css       ← error/success/warning/draft/void — separate namespace
  _dark-mode-tokens.css    ← media query + data-theme overrides
scripts/
  design-check.js          ← linter that enforces no hardcoded hex in components
```

---

## Next file: 03_PHASE2_ICONS.md
