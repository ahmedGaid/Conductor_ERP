import { test } from "../lib/fixtures";
import { expectNoSeriousA11yViolations } from "../lib/a11y";

// Top screens per FILE_06 — a representative list, dashboard, form, and the Settings →
// Accessibility page itself. Runs under both `ar` (RTL, first) and `en` projects automatically,
// since it reuses the suite's authenticated `page` fixture.
const SCREENS: Array<{ name: string; path: string }> = [
  { name: "dashboard", path: "/#/" },
  { name: "sales orders", path: "/#/sales" },
  { name: "purchasing orders", path: "/#/purchasing" },
  { name: "accounting journals", path: "/#/accounting/journals" },
  { name: "inventory stock-on-hand", path: "/#/inventory" },
  { name: "crm pipeline", path: "/#/crm" },
  { name: "new sales order form", path: "/#/sales/orders/new" },
  { name: "settings: accessibility", path: "/#/settings/accessibility" },
];

for (const screen of SCREENS) {
  test(`a11y: ${screen.name} has no serious/critical violations`, async ({ page }) => {
    // `networkidle` hung on screens with background polling (notifications, dashboard widgets),
    // timing out the whole test — Playwright then recycles the worker, forcing a fresh login on
    // every recycled test and cascading into the login-endpoint's 429 rate limit. A bounded wait
    // matches every other spec in this suite (see e.g. sales.spec.ts's `dir`-attribute wait).
    await page.goto(screen.path);
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(2_000);
    await expectNoSeriousA11yViolations(page);
  });
}
