# Phase 0 — Read Codebase & Confirm Understanding
# NO CODE IN THIS FILE. READ ONLY.

---

## Files to read (in order)

Read each file completely before answering the confirmation questions below.

```
1.  src/styles/                   (list all .css / .scss files)
2.  src/styles/variables.css      (or _variables.scss — main CSS vars file)
3.  src/styles/components/        (existing button, badge, layout styles)
4.  src/components/layout/        (LayoutShell, Sidebar, Header components)
5.  src/components/shared/        (Badge, Tag, StatusChip, Icon components)
6.  src/modules/sales/            (any existing Sales module page/component)
7.  src/modules/purchasing/       (any existing Purchasing page/component)
8.  src/router/index.js           (or routes.js — how modules are routed)
9.  package.json                  (what icon libraries, if any, are installed)
10. tailwind.config.js            (if exists — check for existing color overrides)
11. src/App.jsx / App.vue          (root component — how layout is wrapped)
12. src/styles/globals.css         (global resets and root CSS variables)
```

If any of these paths don't exist, find the equivalent file and note the actual path.
Write down the actual paths as you find them — you will need them in later phases.

---

## Confirmation questions

Answer all of these before writing a single line of code:

1. What is the current main CSS variables file path? Does it use CSS custom properties
   (`--var`) or SCSS variables (`$var`)? List the first 5 variable names you see in it.

2. Is there an existing color token system? If yes, what naming convention does it use
   (e.g. `--color-primary`, `--brand-blue`, `--surface-1`)?

3. What component wraps all module pages? (LayoutShell / MainLayout / AppLayout?)
   What is its exact file path?

4. Is there any existing `Badge` or `Tag` component? What props does it accept?
   What file is it in?

5. What icon library is currently installed in package.json? (Heroicons, Lucide,
   FontAwesome, none?) What is the import syntax used in existing components?

6. Are there any existing module-specific CSS classes or files? (e.g. `sales.css`,
   `.module-sales`) If yes, list them all.

7. What CSS framework is used — Tailwind, plain CSS, SCSS, CSS Modules, styled-components?
   How are component styles currently organized?

8. Is there a `src/styles/modules/` directory? If not, confirm you will create it fresh.

---

## Forbidden patterns — memorize these

Do NOT do any of the following at any point in this task:

```
✗ Never hardcode a hex color value anywhere in a .jsx / .vue / .ts / .js component file.
  Colors belong in CSS token files only.

✗ Never apply a module accent color to a button element (button, [type="submit"], .btn-primary).
  Primary action buttons use global brand tokens only.

✗ Never set `color: red` or `background: green` or any named CSS color.
  Always use tokens: var(--module-sales-accent-light), var(--color-status-error), etc.

✗ Never modify an existing component's core layout props (width, height, padding, margin)
  to accommodate module identity. Identity is additive — accent bar, badge, icon only.

✗ Never use more than one icon library. If Lucide is installed, use Lucide.
  If nothing is installed, you will install Phosphor in Phase 2.

✗ Never use a dashed or dotted accent bar. Solid only. The dashed variant
  exists as a last resort in the spec but is explicitly forbidden in this implementation.
```

---

## After answering all 8 questions correctly

Run the project health check:

```bash
npm run dev       # project must start without errors
# OR
yarn dev
# OR
python manage.py runserver   # if Django/Python backend
```

Confirm the app loads. Then open: **02_PHASE1_TOKENS.md**
