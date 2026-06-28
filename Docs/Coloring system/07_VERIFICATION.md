# Final Verification Checklist
# Run every check below. All must pass before closing this task.

---

## Full verification suite

### 1. Token files
```bash
ls src/styles/modules/
# Must show: _module-tokens.css  _status-tokens.css  _dark-mode-tokens.css  _list-view-rules.css  CVD_VALIDATION.md
```

### 2. Component files
```bash
ls src/components/shared/
# Must include: ModuleBadge.*  AccentBar.*  DocumentHeader.*  ModuleCell.*
ls src/icons/
# Must include: module-icon-registry.js
```

### 3. Script files
```bash
ls scripts/
# Must include: design-check.js  cvd-check.js
```

### 4. No hardcoded hex colors in any component or module file
```bash
node scripts/design-check.js
# Must output: [PASS] No hardcoded colors found in component files.
```

### 5. CVD simulation passes (or fails with documented mitigation)
```bash
node scripts/cvd-check.js
# Review output — no unmitigated failures (see Phase 5 mitigation rules)
```

### 6. Global styles still load correctly
```bash
grep "module-tokens\|status-tokens\|dark-mode\|list-view" src/styles/globals.css
# Must show all 4 imports
```

### 7. App starts and existing pages are unaffected
```bash
npm run dev
# Zero new console errors. Existing pages render exactly as before.
```

### 8. Layer boundary — no module tokens in button elements
```bash
grep -r "module-.*-accent\|module-.*-bar" src/components/shared/
# Must NOT appear in any button/submit/action component files
# (Only AccentBar.jsx and ModuleBadge.jsx should reference these tokens)
```

---

## One-second recognition test (manual — do this before closing)

1. Open the app in a browser.
2. Render a `<DocumentHeader>` for each of the 7 modules on a test page.
3. Take a screenshot and convert it to grayscale (any image editor or browser devtools → CSS filter: grayscale(1) on body).
4. In grayscale: can you distinguish all 7 modules by icon shape + badge text alone?
5. If yes: test passes. If no: check that icon family has sufficient shape difference.

---

## Summary of new files created

```
src/
├── styles/
│   └── modules/
│       ├── _module-tokens.css        ← 7 modules × light/dark/tint/text/bar tokens
│       ├── _status-tokens.css        ← error/success/warning/draft/void — separate namespace
│       ├── _dark-mode-tokens.css     ← media query + data-theme overrides
│       ├── _list-view-rules.css      ← no per-row coloring, status chips, doc-id styles
│       └── CVD_VALIDATION.md         ← contrast ratios under 3 CVD simulations
├── icons/
│   └── module-icon-registry.js       ← reserved icon sets + getModuleIcon() helper
└── components/
    └── shared/
        ├── ModuleBadge.jsx           ← module badge: [icon] MODULE LABEL
        ├── AccentBar.jsx             ← 5px solid accent bar (zero border-radius)
        ├── DocumentHeader.jsx        ← composed header: badge → title+bar → docId+status
        └── ModuleCell.jsx            ← monochrome row-level module cell for mixed grids

scripts/
├── design-check.js                   ← linter: no hardcoded hex in components
└── cvd-check.js                      ← CVD simulation for all 7 module accent pairs
```

---

## Modified existing files

| File | Change |
|------|--------|
| `src/styles/globals.css` | Appended 4 `@import` lines at the end — nothing else changed |
| `src/components/layout/LayoutShell.*` | Added optional `module={null}` prop + `data-module` attribute on root div — nothing else changed |

---

## Update the skill

After verifying everything passes, open `/mnt/skills/user/ag-code-instructor/SKILL.md`
and add to the "Learned patterns" section:

```
- conductor-visual-identity (2025): Pure CSS token + component addition task. Zero changes
  to existing styles or layout. Key pattern: module accent as CSS var pair (light/dark),
  status colors in separate --color-status-* namespace. CVD mitigation = icon shape + badge
  text always present — color is tertiary. AccentBar must have border-radius: 0.
  Manufacturing must NOT use red (reserved for status). LayoutShell gets data-module attr only.
```

---

## You are done.

All 7 module identities are now live with:
- Token pairs for light and dark mode
- Separate status color namespace
- Icon registry with reserved metaphor sets per module
- ModuleBadge + AccentBar + DocumentHeader components
- List view rules (no per-row color in single-module; monochrome icon in mixed-module)
- CVD simulation with documented mitigation
- Design-check linter to prevent regressions
