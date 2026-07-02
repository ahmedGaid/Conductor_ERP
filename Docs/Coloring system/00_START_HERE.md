# Conductor ERP — Visual Identity System
# READ THIS FILE FIRST. DO NOT WRITE ANY CODE UNTIL TOLD.

## Your job

You are implementing a **complete visual identity system** for Conductor ERP.
This is a design token + component foundation task. The app is ALREADY WORKING.
You are ADDING a design layer only — you must never break existing functionality.

The system gives each ERP module a subtle but consistent visual identity
so users can recognize which module they're in within one second,
using peripheral vision cues only (accent bar, icon, badge) — not page title text.

Modules covered: Sales, Purchasing, Inventory, Accounting, Manufacturing, CRM, HR.

---

## File order

| File | What it does | Risk |
|------|-------------|------|
| 00_START_HERE.md | This file — master index | None |
| 01_READ_CODEBASE.md | Read project structure, zero code | None |
| 02_PHASE1_TOKENS.md | CSS token schema for all modules + status + dark mode | Zero |
| 03_PHASE2_ICONS.md | Phosphor icon library setup + reserved sets per module | Low |
| 04_PHASE3_COMPONENTS.md | ModuleBadge, AccentBar, LayoutShell components | Low |
| 05_PHASE4_LISTVIEW.md | List view + mixed-module dashboard identity rules | Low |
| 06_PHASE5_CVD.md | CVD simulation check + palette validation utility | Zero |
| 07_VERIFICATION.md | Final checklist + regression test + learned patterns | None |

---

## The rules that must NEVER be broken

1. **Additive only.** You add new files and new CSS classes. You do not rename, delete,
   or restructure any existing component, route, or style file.

2. **Never use color alone.** Every module identity must survive grayscale.
   Every screen must have: accent bar + icon + alphanumeric badge — all three.

3. **Status colors live in a separate namespace.** `--color-status-*` tokens must
   never share a hue with any module accent. They are never the same token.

4. **Primary action buttons are global.** `Save`, `Submit`, `Post`, `Approve` buttons
   must use the global brand color only — never the module accent color.
   Never override button color based on which module is active.

5. **Layout grid is rigid.** Sidebar width, header height, action bar position, table
   column alignment — these are locked across ALL modules. Only the data fields inside
   the form change per transaction type.

6. **Dark mode is required.** Every token must have a light and dark variant defined
   from day one. Never hardcode a hex value that only works on white backgrounds.

7. **Phosphor icons only.** No mixing of icon libraries. Every module has a reserved
   metaphor subset — the agent must reject any icon outside that subset.

---

## After every phase, run:

```bash
# In project root:
node scripts/design-check.js   # token linter (created in Phase 1)
# OR if no build system:
grep -r "hardcoded-color\|#[0-9a-fA-F]\{6\}" src/styles/modules/ # must return nothing
```

---

## Now open: 01_READ_CODEBASE.md
