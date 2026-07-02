# Phase 4 — List View & Mixed-Module Dashboard Identity
# LOW RISK — New components + CSS only. No existing list components modified.

---

## What you will do in this phase

1. Create `src/components/shared/ModuleCell.jsx` — module identity cell for data grids
2. Create `src/styles/modules/_list-view-rules.css` — list view identity CSS rules
3. Document the rules for when to use/not use module color in list contexts

---

## The rules you must understand before writing code

```
RULE 1 — Single-module list pages (e.g., /sales/invoices):
  - The page-level DocumentHeader + LayoutShell data-module attribute
    already establish module identity.
  - DO NOT add per-row color bars, colored cells, or tinted rows.
  - Color per row = visual noise multiplied by row count. Forbidden.

RULE 2 — Mixed-module dashboards (e.g., "Recent Transactions", "My Approvals"):
  - Each row originates from a different module.
  - Use a 16×16 monochrome icon from the module's reserved icon set.
  - Add a short text label next to the icon (e.g., "Sales", "PUR").
  - NO color bars per row. NO colored cells. NO tinted backgrounds.
  - The icon + text label is the ONLY module identity at the row level.
  - Color is context-bound to module scope — not row scope.

RULE 3 — The module icon column:
  - Position: first column, before document number.
  - Width: fixed 120px (icon 16px + gap 6px + text label).
  - Icon: monochrome (use currentColor, not accent color token) at 16×16.
  - Text: 12px, font-weight 500, color: text-secondary.
```

---

## Step 1 — Create `src/components/shared/ModuleCell.jsx`

Used in mixed-module data grids. Renders module identity in a single table cell.

```jsx
/**
 * ModuleCell — Module identity cell for mixed-module data grids.
 *
 * Used in: "Recent Transactions", "Approvals Queue", any mixed-module list.
 * NOT used in: single-module list pages (Sales Invoice List, PO List, etc.)
 *
 * USAGE:
 *   <ModuleCell module="sales" />
 *   <ModuleCell module="purchasing" />
 *
 * Rules:
 * - Icon is MONOCHROME (currentColor / text-secondary) — not accent colored.
 * - No background tint, no accent bar, no border.
 * - Size: icon 16px, text 12px, gap 6px.
 * - This intentionally looks quiet — module color is NOT used at row level.
 */

import React from 'react';
import { getModuleIcon, MODULE_ICONS } from '../../icons/module-icon-registry';

export default function ModuleCell({ module }) {
  const Icon = getModuleIcon(module, 'default');
  if (!Icon) return <span style={{ color: 'var(--text-secondary, #6B7280)', fontSize: 12 }}>—</span>;

  const label = MODULE_ICONS[module]?.badge || module.toUpperCase().slice(0, 3);

  return (
    <span
      className="conductor-module-cell"
      style={{
        display:    'inline-flex',
        alignItems: 'center',
        gap:        6,
        color:      'var(--text-secondary, #6B7280)',
        /* Intentionally NOT using accent color token — monochrome at row level */
      }}
    >
      <Icon
        size={16}
        weight="regular"
        color="currentColor"
        aria-hidden="true"
      />
      <span style={{ fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap' }}>
        {label}
      </span>
    </span>
  );
}
```

---

## Step 2 — Create `src/styles/modules/_list-view-rules.css`

```css
/* ============================================================
   CONDUCTOR ERP — LIST VIEW IDENTITY RULES
   ============================================================ */

/* ── Single-module list pages ──────────────────────────────────
   Identity is provided by the page-level header only.
   No per-row coloring. */
.conductor-data-table tr {
  background: transparent;
  /* Do NOT add background color here even for hover — use existing table hover */
}

/* ── Mixed-module dashboard tables ────────────────────────────
   The module column has fixed width and is always first. */
.conductor-data-table .col-module {
  width:        120px;
  min-width:    120px;
  max-width:    120px;
  padding-left: 12px;
}

/* ── Prevent accidental module color leaking into rows ────────
   If a developer accidentally applies a module tint class to a row,
   this override strips it. */
.conductor-data-table tr[data-module-row] {
  background: transparent !important;
  border-left: none !important;
}

/* ── Document ID column — always monospace ─────────────────── */
.conductor-data-table .col-document-id {
  font-family: monospace;
  font-size:   13px;
  color:       var(--text-secondary, #6B7280);
}

/* ── Status column chips ───────────────────────────────────── */
.conductor-status-chip {
  display:       inline-block;
  padding:       2px 8px;
  border-radius: 4px;
  font-size:     12px;
  font-weight:   500;
}

.conductor-status-chip[data-status="draft"] {
  background: var(--color-status-draft-bg);
  border:     1px solid var(--color-status-draft-border);
  color:      var(--color-status-draft-text);
}

.conductor-status-chip[data-status="approved"],
.conductor-status-chip[data-status="posted"] {
  background: var(--color-status-success-bg);
  border:     1px solid var(--color-status-success-border);
  color:      var(--color-status-success-text);
}

.conductor-status-chip[data-status="void"] {
  background: var(--color-status-void-bg);
  border:     1px solid var(--color-status-void-border);
  color:      var(--color-status-void-text);
}

.conductor-status-chip[data-status="error"] {
  background: var(--color-status-error-bg);
  border:     1px solid var(--color-status-error-border);
  color:      var(--color-status-error-text);
}
```

---

## Step 3 — Append import to globals.css

Open `src/styles/globals.css` and **append** one line (after the three imports from Phase 1):

```css
@import './modules/_list-view-rules.css';
```

---

## Step 4 — Update the existing module-tokens import section comment

Find the comment block you added in Phase 1 in globals.css and update it:

```css
/* Conductor ERP — Module Identity System */
@import './modules/_module-tokens.css';
@import './modules/_status-tokens.css';
@import './modules/_dark-mode-tokens.css';
@import './modules/_list-view-rules.css';
```

---

## Verification for Phase 4

```bash
# 1. ModuleCell exists
ls src/components/shared/ModuleCell.*

# 2. List view rules CSS exists
ls src/styles/modules/_list-view-rules.css

# 3. Import was added to globals
grep "list-view-rules" src/styles/globals.css

# 4. No hardcoded colors
node scripts/design-check.js

# 5. App still starts
npm run dev
```

---

## What you just built

```
src/components/shared/
  ModuleCell.jsx            ← monochrome module cell for mixed-module data grids
src/styles/modules/
  _list-view-rules.css      ← enforces no per-row coloring, status chips, doc-id style
```

---

## Next file: 06_PHASE5_CVD.md
