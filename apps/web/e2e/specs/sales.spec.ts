import { test, expect } from "../lib/fixtures";
import type { ApiGet } from "../lib/api";

// Prerequisite: `scripts/seed_demo.py` master data (customer ACME, warehouse MAIN, item WIDGET,
// tax code VAT14 via `manage.py seed_accounting`, and the STANDARD price list's WIDGET line) —
// see Docs/RUNBOOK.md "Regression run before every release". The order itself is created fresh
// here (not reused from the seed) so the suite is safe to re-run against any DB state.
interface SalesOrderApi {
  id: string;
  status: string;
  subtotal_minor: number;
  tax_minor: number;
  invoiced_minor: number;
  paid_minor: number;
  outstanding_minor: number;
}

// Click a lifecycle button, then wait for the SERVER (not the optimistic UI) to reach
// `wantStatus`, then reload so the next click acts on a page that reflects that confirmed state.
// A page reload after only an optimistic client update — with a slow, out-of-order earlier fetch
// still in flight — was observed to redraw the PRE-action state (see DECISIONS.md); polling the
// API first, and treating it as the sole source of truth for gating, sidesteps that race.
async function runStep<T extends { status: string }>(
  page: import("@playwright/test").Page,
  apiGet: ApiGet,
  path: string,
  buttonLabel: string,
  wantStatus: string,
): Promise<void> {
  await page.getByRole("button", { name: buttonLabel, exact: true }).first().click();
  await expect(async () => {
    expect((await apiGet<T>(path)).status).toBe(wantStatus);
  }).toPass();
  await page.reload();
}

test("app root carries the correct text direction for this locale", async ({ page, appLocale }) => {
  await page.goto("/#/");
  await expect(page.locator("html")).toHaveAttribute("dir", appLocale === "ar" ? "rtl" : "ltr");
  // Let the boot sequence's own background requests (setup status, preferences, dashboard
  // widgets) finish before the test — and this page — tears down. Ending the test while one of
  // those is still in flight can abort it mid-request; if that happened to be a refresh-token
  // rotation, the browser never applies the server's new cookie, leaving the WORKER-shared
  // context's cookie one rotation behind for whichever test's page boots next.
  await page.waitForLoadState("networkidle");
});

test("sales: create -> confirm -> deliver -> invoice -> partial pay -> pay in full", async ({
  page,
  t,
  apiGet,
}) => {
  await page.goto("/#/sales/orders/new");

  await page.getByLabel(t("sales.orders.customer")).selectOption("ACME");
  await page.getByLabel(t("inventory.warehouse.label")).selectOption("MAIN");
  await page.getByLabel(t("sales.newOrder.taxCode")).selectOption("VAT14");

  const line = page.locator(".sales-table tbody tr").first();
  // Quantity BEFORE item: picking the item auto-resolves its price for the current customer+qty
  // (STANDARD price list, WIDGET base 150.00 below the qty>=10 tier — see scripts/seed_demo.py
  // seed_pricing). Picking the item first and overwriting the field afterwards races that
  // in-flight resolve call, which can silently clobber a manually-typed price back to 150.00.
  await line.locator("input").nth(0).fill("5"); // quantity
  await line.locator("select").selectOption("WIDGET");
  await expect(line.locator("input").nth(1)).toHaveValue("150.00"); // resolved unit price

  await page.getByRole("button", { name: t("sales.newOrder.create"), exact: true }).click();
  await page.waitForURL(/#\/sales\/orders\/[0-9a-f-]{36}$/);
  const orderId = page.url().split("/").pop()!;
  const orderPath = `/sales/orders/${orderId}`;

  // Business-layer check in integer minor units (net 750.00). VAT isn't booked until Invoice
  // (double-entry: no VAT liability exists before the invoice posts it) — checked below instead.
  let order = await apiGet<SalesOrderApi>(orderPath);
  expect(order.subtotal_minor).toBe(75_000);
  expect(order.status).toBe("draft");

  await runStep<SalesOrderApi>(page, apiGet, orderPath, t("sales.detail.confirm"), "confirmed");
  await runStep<SalesOrderApi>(page, apiGet, orderPath, t("sales.detail.deliver"), "delivered");
  await runStep<SalesOrderApi>(page, apiGet, orderPath, t("sales.detail.invoice"), "invoiced");

  // VAT14 (14%) posts at invoice time: net 750.00 -> tax 105.00 -> gross 855.00.
  order = await apiGet<SalesOrderApi>(orderPath);
  expect(order.tax_minor).toBe(10_500);
  expect(order.invoiced_minor).toBe(85_500);

  // Partial payment (delivery-readiness FILE_05): order stays open with a reduced balance.
  await page.getByRole("button", { name: t("sales.detail.recordPayment"), exact: true }).click();
  await page.getByLabel(t("document.paymentDialog.amount")).fill("300.00");
  await page.getByRole("button", { name: t("document.paymentDialog.confirm"), exact: true }).click();

  await expect(async () => {
    order = await apiGet<SalesOrderApi>(orderPath);
    expect(order.paid_minor).toBe(30_000);
  }).toPass();
  expect(order.outstanding_minor).toBe(55_500);
  expect(order.status).toBe("invoiced");
  await page.reload();

  // Final payment (dialog defaults to the remaining outstanding) settles the order in full.
  await page.getByRole("button", { name: t("sales.detail.recordPayment"), exact: true }).click();
  await page.getByRole("button", { name: t("document.paymentDialog.confirm"), exact: true }).click();

  await expect(async () => {
    order = await apiGet<SalesOrderApi>(orderPath);
    expect(order.status).toBe("paid");
  }).toPass();
  expect(order.paid_minor).toBe(85_500);
  expect(order.outstanding_minor).toBe(0);
});
