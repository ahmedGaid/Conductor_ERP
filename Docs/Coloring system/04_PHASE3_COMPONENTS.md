# Phase 3 — Core Identity Components
# LOW RISK — New components only. LayoutShell gets one additive prop.

---

## What you will do in this phase

1. Create `src/components/shared/ModuleBadge.jsx`
2. Create `src/components/shared/AccentBar.jsx`
3. Create `src/components/shared/DocumentHeader.jsx` — composes badge + bar + title + status
4. Add optional `module` prop to the existing LayoutShell — DO NOT change any other props

---

## Step 1 — Create `src/components/shared/ModuleBadge.jsx`

```jsx
/**
 * ModuleBadge — Module identity badge shown above every transaction page title.
 *
 * Renders:    [ICON] SALES
 * Or:         [ICON↩] SALES   (when isReversal=true — icon gets reversal indicator)
 *
 * USAGE:
 *   <ModuleBadge module="sales" />
 *   <ModuleBadge module="purchasing" isReversal={true} />
 *
 * Rules:
 * - Background uses --module-{name}-tint-light (very soft tint)
 * - Text uses --module-{name}-text-light (dark enough for contrast)
 * - Font: 11px uppercase, letter-spacing 0.08em, font-weight 500
 * - Never change badge size or font weight per-module — always identical structure
 */

import React from 'react';
import ModuleIcon from './ModuleIcon';
import { MODULE_ICONS } from '../../icons/module-icon-registry';

const MODULE_VARS = {
  sales:         { tint: '--module-sales-tint-light',         text: '--module-sales-text-light',         border: '--module-sales-accent-light' },
  purchasing:    { tint: '--module-purchasing-tint-light',    text: '--module-purchasing-text-light',    border: '--module-purchasing-accent-light' },
  inventory:     { tint: '--module-inventory-tint-light',     text: '--module-inventory-text-light',     border: '--module-inventory-accent-light' },
  accounting:    { tint: '--module-accounting-tint-light',    text: '--module-accounting-text-light',    border: '--module-accounting-accent-light' },
  manufacturing: { tint: '--module-manufacturing-tint-light', text: '--module-manufacturing-text-light', border: '--module-manufacturing-accent-light' },
  crm:           { tint: '--module-crm-tint-light',           text: '--module-crm-text-light',           border: '--module-crm-accent-light' },
  hr:            { tint: '--module-hr-tint-light',            text: '--module-hr-text-light',            border: '--module-hr-accent-light' },
};

export default function ModuleBadge({ module, isReversal = false }) {
  const vars = MODULE_VARS[module];
  if (!vars) return null;

  const label = MODULE_ICONS[module]?.label || module.toUpperCase();

  return (
    <span
      className="conductor-module-badge"
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        gap:            6,
        padding:        '3px 10px',
        borderRadius:   4,
        background:     `var(${vars.tint})`,
        border:         `1px solid var(${vars.border})`,
        fontSize:       11,
        fontWeight:     500,
        letterSpacing:  '0.08em',
        textTransform:  'uppercase',
        color:          `var(${vars.text})`,
        userSelect:     'none',
      }}
    >
      <ModuleIcon
        module={module}
        type="default"
        size={13}
        isReversal={isReversal}
      />
      {label}
    </span>
  );
}
```

---

## Step 2 — Create `src/components/shared/AccentBar.jsx`

```jsx
/**
 * AccentBar — 5px vertical bar placed to the left of the page title block.
 * Creates immediate peripheral-vision module recognition.
 *
 * USAGE:
 *   <AccentBar module="sales" />
 *
 * Rules:
 * - Width: exactly 5px. Never change this value.
 * - Height: matches parent container (use align-self: stretch or explicit height).
 * - Border-radius: 0 (no rounded corners on single-sided borders).
 * - Solid fill only — never dashed, never dotted.
 * - Uses --module-{name}-bar token (auto-switches light/dark via CSS).
 */

import React from 'react';

export default function AccentBar({ module, height = 48 }) {
  return (
    <div
      className="conductor-accent-bar"
      aria-hidden="true"
      style={{
        width:          5,
        height:         height,
        borderRadius:   0,
        background:     `var(--module-${module}-bar)`,
        flexShrink:     0,
      }}
    />
  );
}
```

---

## Step 3 — Create `src/components/shared/DocumentHeader.jsx`

This is the composed header used at the top of every transaction detail page.
It assembles: Badge → Title+AccentBar row → DocumentID + StatusTag.

```jsx
/**
 * DocumentHeader — Full page identity header for transaction detail pages.
 *
 * Visual hierarchy (top to bottom):
 *   1. ModuleBadge       (module label + icon)
 *   2. AccentBar + Title (large title with left accent bar)
 *   3. Document ID + Status tag
 *
 * USAGE:
 *   <DocumentHeader
 *     module="sales"
 *     title="Sales Invoice"
 *     documentId="SI-000123"
 *     status="draft"               // draft | approved | posted | void
 *     isReversal={false}           // true for credit notes, returns
 *   />
 *
 * Rules:
 * - Title font: 24px, font-weight 500 — never change per-module
 * - DocumentId font: 13px, color: text-secondary — always same style
 * - Status tag uses --color-status-* tokens only
 * - This component never receives a color prop — color comes from module name
 */

import React from 'react';
import ModuleBadge from './ModuleBadge';
import AccentBar from './AccentBar';

const STATUS_STYLES = {
  draft: {
    bg:     'var(--color-status-draft-bg)',
    border: 'var(--color-status-draft-border)',
    text:   'var(--color-status-draft-text)',
    label:  'Draft',
  },
  approved: {
    bg:     'var(--color-status-success-bg)',
    border: 'var(--color-status-success-border)',
    text:   'var(--color-status-success-text)',
    label:  'Approved',
  },
  posted: {
    bg:     'var(--color-status-success-bg)',
    border: 'var(--color-status-success-border)',
    text:   'var(--color-status-success-text)',
    label:  'Posted',
  },
  void: {
    bg:     'var(--color-status-void-bg)',
    border: 'var(--color-status-void-border)',
    text:   'var(--color-status-void-text)',
    label:  'Void',
  },
  error: {
    bg:     'var(--color-status-error-bg)',
    border: 'var(--color-status-error-border)',
    text:   'var(--color-status-error-text)',
    label:  'Error',
  },
};

function StatusTag({ status }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.draft;
  return (
    <span style={{
      display:      'inline-block',
      padding:      '2px 9px',
      borderRadius: 4,
      background:   style.bg,
      border:       `1px solid ${style.border}`,
      fontSize:     12,
      fontWeight:   500,
      color:        style.text,
      letterSpacing:'0.04em',
    }}>
      {style.label}
    </span>
  );
}

export default function DocumentHeader({
  module,
  title,
  documentId,
  status = 'draft',
  isReversal = false,
}) {
  return (
    <div className="conductor-document-header" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* 1. Module Badge */}
      <div>
        <ModuleBadge module={module} isReversal={isReversal} />
      </div>

      {/* 2. Accent Bar + Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <AccentBar module={module} height={36} />
        <h1 style={{
          margin:     0,
          fontSize:   24,
          fontWeight: 500,
          lineHeight: 1.2,
        }}>
          {title}
        </h1>
      </div>

      {/* 3. Document ID + Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingRight: 19 }}>
        <span style={{ fontSize: 13, color: 'var(--text-secondary, #6B7280)', fontFamily: 'monospace' }}>
          {documentId}
        </span>
        <StatusTag status={status} />
      </div>
    </div>
  );
}
```

---

## Step 4 — Add `module` prop to existing LayoutShell

Open the existing LayoutShell component (path found in Phase 0).
**Append only** — add the optional `module` prop.
Do not change any existing props, layout structure, or styles.

Find the component's props definition and add `module` with a default of `null`.
Then add a data attribute to the root element so CSS can target it:

```jsx
// BEFORE (example — your actual code may differ):
export default function LayoutShell({ children }) {
  return <div className="layout-shell">{children}</div>;
}

// AFTER — only add the module prop and data attribute:
export default function LayoutShell({ children, module = null }) {
  return (
    <div
      className="layout-shell"
      data-module={module || undefined}
    >
      {children}
    </div>
  );
}
```

This `data-module` attribute allows future CSS scoping if needed.
It never changes any visual layout — it is a metadata attribute only.

---

## Verification for Phase 3

```bash
# 1. All three new components exist
ls src/components/shared/ModuleBadge.*
ls src/components/shared/AccentBar.*
ls src/components/shared/DocumentHeader.*

# 2. No hardcoded hex values in new components
node scripts/design-check.js

# 3. App still starts and existing pages are unaffected
npm run dev

# 4. Quick smoke test — create a temp test page that renders DocumentHeader:
# Add this temporarily to any existing dev page to verify visual output:
# <DocumentHeader module="sales" title="Sales Invoice" documentId="SI-000001" status="draft" />
# <DocumentHeader module="purchasing" title="Purchase Invoice" documentId="PI-000001" status="approved" />
# <DocumentHeader module="manufacturing" title="Work Order" documentId="WO-000001" status="posted" isReversal={false} />
# Visually confirm: each shows different accent bar color + badge + correct status tag
# Remove test code after confirmation.
```

---

## What you just built

```
src/components/shared/
  ModuleBadge.jsx        ← module identity badge (icon + label + soft tint background)
  AccentBar.jsx          ← 5px solid vertical accent bar (color via CSS token)
  DocumentHeader.jsx     ← composed header: badge → title+bar → docId + status tag
```

LayoutShell: one new optional `module` prop added, nothing else changed.

---

## Next file: 05_PHASE4_LISTVIEW.md
