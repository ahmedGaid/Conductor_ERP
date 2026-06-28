# Phase 2 — Icon Library Setup & Reserved Sets
# LOW RISK — New files + one package install. No existing components modified.

---

## What you will do in this phase

1. Check if Phosphor Icons is installed. If not, install it.
2. Create `src/icons/module-icon-registry.js` — the single source of truth for all module icons.
3. Create `src/components/shared/ModuleIcon.jsx` (or `.vue`) — the enforced icon wrapper.

---

## Step 1 — Install Phosphor Icons (only if not already installed)

Check `package.json`. If `@phosphor-icons/react` (or `@phosphor-icons/vue`) is NOT listed:

```bash
# For React projects:
npm install @phosphor-icons/react

# For Vue projects:
npm install @phosphor-icons/vue

# For plain HTML/vanilla JS:
npm install @phosphor-icons/web
```

If the project already uses Lucide or Heroicons, **do not replace them**.
In that case, skip the install and use the existing library.
Map the reserved icon sets in Step 2 to the equivalent icons from the installed library.
Document the mapping in a comment at the top of the registry file.

---

## Step 2 — Create `src/icons/module-icon-registry.js`

```javascript
/**
 * CONDUCTOR ERP — MODULE ICON REGISTRY
 *
 * This file is the single source of truth for module icons.
 * Rules:
 * - Each module has a reserved metaphor subset (3 icons max per transaction type).
 * - All icons share identical stroke weight (1.5px / "regular" weight in Phosphor).
 * - Do NOT import icons from outside this registry in any module component.
 * - If you need an icon not listed here, ADD it to this file first, then use it.
 * - Icons for status/reversal indicators are listed separately — do not mix.
 */

// ─── React import (change to @phosphor-icons/vue for Vue projects) ───
import {
  // Sales
  Tag, ShoppingCart, Receipt, ArrowUUpLeft as SalesReturn,
  // Purchasing
  Truck, Package, ClipboardList, ArrowUUpRight as PurchaseReturn,
  // Inventory
  Archive, ArrowsLeftRight as InventoryTransfer, Barcode,
  // Accounting
  BookOpen, CurrencyDollar, Scales,
  // Manufacturing
  Wrench, Factory, Gear,
  // CRM
  UsersThree, HandshakeLight as Handshake, Megaphone,
  // HR
  IdentificationCard, CalendarBlank, ChartBar,
  // Shared / Layout
  ArrowCounterClockwise as ReversalIndicator,
  WarningCircle, CheckCircle, Clock, XCircle,
} from '@phosphor-icons/react';

export const MODULE_ICONS = {
  sales: {
    default:        Tag,
    invoice:        Receipt,
    order:          ShoppingCart,
    return:         SalesReturn,
    label:          'Sales',
    badge:          'SLS',
  },
  purchasing: {
    default:        ClipboardList,
    invoice:        Receipt,
    order:          Truck,
    return:         PurchaseReturn,
    label:          'Purchasing',
    badge:          'PUR',
  },
  inventory: {
    default:        Archive,
    transfer:       InventoryTransfer,
    item:           Barcode,
    label:          'Inventory',
    badge:          'INV',
  },
  accounting: {
    default:        BookOpen,
    journal:        Scales,
    payment:        CurrencyDollar,
    label:          'Accounting',
    badge:          'ACC',
  },
  manufacturing: {
    default:        Factory,
    workOrder:      Wrench,
    bom:            Gear,
    label:          'Manufacturing',
    badge:          'MFG',
  },
  crm: {
    default:        UsersThree,
    lead:           Handshake,
    campaign:       Megaphone,
    label:          'CRM',
    badge:          'CRM',
  },
  hr: {
    default:        IdentificationCard,
    attendance:     CalendarBlank,
    payroll:        ChartBar,
    label:          'HR',
    badge:          'HR',
  },
};

// ─── Status icons (separate — never used as module identity) ───────────
export const STATUS_ICONS = {
  error:    WarningCircle,
  success:  CheckCircle,
  draft:    Clock,
  void:     XCircle,
  reversal: ReversalIndicator,   // Used in badge icon only for reverse transactions
};

// ─── Helper: get icon component by module + transaction type ───────────
export function getModuleIcon(module, type = 'default') {
  const mod = MODULE_ICONS[module];
  if (!mod) {
    console.warn(`[ModuleIconRegistry] Unknown module: "${module}"`);
    return null;
  }
  const Icon = mod[type] || mod.default;
  return Icon;
}
```

---

## Step 3 — Create `src/components/shared/ModuleIcon.jsx`

```jsx
/**
 * ModuleIcon — Enforced icon wrapper for Conductor ERP modules.
 *
 * USAGE:
 *   <ModuleIcon module="sales" type="invoice" size={20} />
 *   <ModuleIcon module="purchasing" type="default" size={16} />
 *
 * This component is the ONLY way to render module icons in the app.
 * Direct imports from @phosphor-icons/react inside module pages are forbidden.
 */

import React from 'react';
import { getModuleIcon, STATUS_ICONS } from '../../icons/module-icon-registry';

const MODULE_TOKEN_MAP = {
  sales:          '--module-sales-accent-light',
  purchasing:     '--module-purchasing-accent-light',
  inventory:      '--module-inventory-accent-light',
  accounting:     '--module-accounting-accent-light',
  manufacturing:  '--module-manufacturing-accent-light',
  crm:            '--module-crm-accent-light',
  hr:             '--module-hr-accent-light',
};

export default function ModuleIcon({
  module,
  type = 'default',
  size = 20,
  isReversal = false,   // true = show reversal indicator overlay
  className = '',
  'aria-hidden': ariaHidden = true,
}) {
  const Icon = getModuleIcon(module, type);
  if (!Icon) return null;

  const tokenVar = MODULE_TOKEN_MAP[module] || '--module-sales-accent-light';
  const iconColor = `var(${tokenVar})`;

  return (
    <span
      className={`conductor-module-icon ${className}`}
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}
    >
      <Icon
        size={size}
        weight="regular"
        color={iconColor}
        aria-hidden={ariaHidden}
      />
      {isReversal && (
        <STATUS_ICONS.reversal
          size={Math.round(size * 0.55)}
          weight="bold"
          color="var(--color-reversal-indicator)"
          style={{
            position: 'absolute',
            bottom: -2,
            right: -4,
          }}
          aria-label="Reversal transaction"
          aria-hidden={false}
        />
      )}
    </span>
  );
}
```

---

## Vue version (create instead if project uses Vue)

Create `src/components/shared/ModuleIcon.vue`:

```vue
<template>
  <span class="conductor-module-icon" style="position: relative; display: inline-flex; align-items: center;">
    <component
      :is="Icon"
      :size="size"
      weight="regular"
      :color="`var(${tokenVar})`"
      aria-hidden="true"
    />
    <component
      v-if="isReversal"
      :is="STATUS_ICONS.reversal"
      :size="Math.round(size * 0.55)"
      weight="bold"
      color="var(--color-reversal-indicator)"
      style="position: absolute; bottom: -2px; right: -4px;"
      aria-label="Reversal transaction"
    />
  </span>
</template>

<script setup>
import { computed } from 'vue';
import { getModuleIcon, STATUS_ICONS } from '../../icons/module-icon-registry';

const props = defineProps({
  module: { type: String, required: true },
  type:   { type: String, default: 'default' },
  size:   { type: Number, default: 20 },
  isReversal: { type: Boolean, default: false },
});

const MODULE_TOKEN_MAP = {
  sales: '--module-sales-accent-light',
  purchasing: '--module-purchasing-accent-light',
  inventory: '--module-inventory-accent-light',
  accounting: '--module-accounting-accent-light',
  manufacturing: '--module-manufacturing-accent-light',
  crm: '--module-crm-accent-light',
  hr: '--module-hr-accent-light',
};

const Icon = computed(() => getModuleIcon(props.module, props.type));
const tokenVar = computed(() => MODULE_TOKEN_MAP[props.module] || '--module-sales-accent-light');
</script>
```

---

## Verification for Phase 2

```bash
# 1. Confirm icon registry exists
cat src/icons/module-icon-registry.js

# 2. Confirm ModuleIcon component exists
ls src/components/shared/ModuleIcon.*

# 3. Confirm Phosphor is installed (or existing library still works)
node -e "require('@phosphor-icons/react'); console.log('OK')"

# 4. No new hardcoded colors
node scripts/design-check.js

# 5. App still starts
npm run dev
```

---

## What you just built

```
src/icons/
  module-icon-registry.js    ← single source of truth for all module icons
src/components/shared/
  ModuleIcon.jsx              ← enforced icon wrapper (or .vue for Vue projects)
```

---

## Next file: 04_PHASE3_COMPONENTS.md
