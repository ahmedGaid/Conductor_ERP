import { test, expect } from "../lib/fixtures";
import { pickCombo } from "../lib/combobox";

// Prerequisite: `scripts/seed_demo.py` master data (customer ACME, price list STANDARD, item
// GADGET) — see Docs/RUNBOOK.md "Regression run before every release".

interface LeadApi {
  id: string;
  name: string;
  status: string;
}

test("crm: add lead -> convert flips its status", async ({ page, t, apiGet }) => {
  await page.goto("/#/crm/leads");

  const leadName = `E2E Lead ${Date.now()}`;
  await page.getByLabel(t("crm.lead.name")).fill(leadName);
  await page.getByLabel(t("crm.lead.company")).fill("E2E Test Co");
  await page.getByRole("button", { name: t("crm.lead.add"), exact: true }).click();

  const row = page.locator("table tbody tr", { hasText: leadName });
  await expect(row).toBeVisible();
  await expect(row.getByText(t("crm.leadStatus.new"), { exact: true })).toBeVisible();

  // The row appears instantly as an optimistic placeholder (empty code, temp id) before the real
  // `createLead` response replaces it — confirm the REAL lead exists server-side first, or a
  // Convert click that lands before the swap fires against the temp id and silently no-ops.
  await expect(async () => {
    const leads = await apiGet<LeadApi[]>("/crm/leads");
    expect(leads.some((l) => l.name === leadName)).toBe(true);
  }).toPass();

  await row.getByRole("button", { name: t("crm.lead.convert"), exact: true }).click();
  // Confirm server-side, then reload, before trusting the row's badge — an optimistic update here
  // can otherwise be overwritten by an in-flight stale list refetch from the initial page load.
  await expect(async () => {
    const leads = await apiGet<LeadApi[]>("/crm/leads");
    expect(leads.find((l) => l.name === leadName)?.status).toBe("converted");
  }).toPass();
  await page.reload();
  await expect(row.getByText(t("crm.leadStatus.converted"), { exact: true })).toBeVisible();
});

test("pricing: a qty-tiered price line resolves ahead of the base price in a sales order", async ({
  page,
  t,
}) => {
  // Open the STANDARD price list from the list page (its route needs the list's id, not its code).
  await page.goto("/#/pricing");
  await page.getByRole("link", { name: "STANDARD" }).click();
  await page.waitForURL(/#\/pricing\/[0-9a-f-]{36}$/);

  // Scoped to the add-line form: the price list's EXISTING rows each carry an "Edit Unit price"
  // inline-edit button, whose accessible name also contains "Unit price" and would otherwise
  // make a page-wide getByLabel("Unit price") match 10+ elements.
  const addForm = page.locator("form.pricing-toolbar");
  await pickCombo(page, addForm.getByLabel(t("pricing.detail.item")), "GADGET");
  await addForm.getByLabel(t("pricing.detail.unitPrice")).fill("250.00");
  await addForm.getByLabel(t("pricing.detail.minQty")).fill("20"); // tier: qty >= 20 -> 250.00
  await addForm.getByRole("button", { name: t("pricing.detail.addLine") }).click();
  // `.first()`: re-running this spec against a DB that already has this exact tier line (from a
  // prior run — price lines aren't deduplicated) would otherwise make this locator match 2+ rows.
  const gadgetTierRow = page
    .locator(".pricing-table tbody tr", { hasText: "GADGET" })
    .filter({ hasText: "20" })
    .first();
  await expect(gadgetTierRow).toBeVisible();

  // A new sales order for ACME: qty below the tier resolves the base price (300.00, seeded by
  // scripts/seed_demo.py seed_pricing); qty at/above the tier resolves the new 250.00 line.
  await page.goto("/#/sales/orders/new");
  await pickCombo(page, page.getByLabel(t("sales.orders.customer")), "ACME");

  const line = page.locator(".sales-table tbody tr").first();
  await line.locator("input").nth(0).fill("5"); // qty below the tier
  await pickCombo(page, line.locator(".combobox-trigger"), "GADGET");
  await expect(line.locator("input").nth(1)).toHaveValue("300.00");

  await line.locator("input").nth(0).fill("25"); // qty at/above the tier
  // Re-pick (same option) to re-trigger price resolution at the new qty — ComboBox's onChange
  // fires unconditionally on pick, so no need to clear first like the native <select> it replaced.
  await pickCombo(page, line.locator(".combobox-trigger"), "GADGET");
  await expect(line.locator("input").nth(1)).toHaveValue("250.00");
});
