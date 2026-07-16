import { test, expect } from "../lib/fixtures";
import type { ApiGet } from "../lib/api";

// Prerequisite: `scripts/seed_demo.py` master data (supplier GLOBEX, warehouse MAIN) — see
// Docs/RUNBOOK.md "Regression run before every release". The request/order are created fresh
// here so the suite is safe to re-run against any DB state.
interface PurchaseRequestApi {
  id: string;
  status: string;
  subtotal_minor: number;
  converted_order_number: string;
}

interface PurchaseOrderApi {
  id: string;
  status: string;
  approved: boolean;
  subtotal_minor: number;
  received_minor: number;
  billed_minor: number;
  paid_minor: number;
  outstanding_minor: number;
}

// Click a lifecycle button, then wait for the SERVER (not the optimistic UI) to reach
// `wantStatus`, then reload so the next click acts on a page that reflects that confirmed state.
// A page reload after only an optimistic client update — with a slow, out-of-order earlier
// fetch still in flight — was observed to redraw the PRE-action state (see DECISIONS.md); polling
// the API first, and treating it as the sole source of truth for gating, sidesteps that race.
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

test("purchasing: request -> approve -> convert -> receive -> bill -> partial pay -> pay in full", async ({
  page,
  t,
  apiGet,
}) => {
  // Above the 10,000 approval threshold (see scripts/seed_demo.py seed_discounts_and_approval),
  // so the request needs an explicit Approve, not just Submit.
  await page.goto("/#/purchasing/requests/new");
  await page.getByLabel(t("purchasing.orders.supplier")).selectOption("GLOBEX");
  await page.getByLabel(t("inventory.warehouse.label")).selectOption("MAIN");

  const line = page.locator(".pur-table tbody tr").first();
  await line.locator("select").selectOption("WIDGET");
  await line.locator("input").nth(0).fill("200"); // quantity
  await line.locator("input").nth(1).fill("80.00"); // unit cost -> 16,000.00

  await page.getByRole("button", { name: t("purchasing.requests.create"), exact: true }).click();
  await page.waitForURL(/#\/purchasing\/requests\/[0-9a-f-]{36}$/);
  const requestId = page.url().split("/").pop()!;
  const requestPath = `/purchasing/requests/${requestId}`;

  let request = await apiGet<PurchaseRequestApi>(requestPath);
  expect(request.subtotal_minor).toBe(1_600_000);
  expect(request.status).toBe("draft");

  await runStep<PurchaseRequestApi>(page, apiGet, requestPath, t("purchasing.requests.submit"), "submitted");
  await runStep<PurchaseRequestApi>(page, apiGet, requestPath, t("purchasing.requests.approve"), "approved");

  await page.getByRole("button", { name: t("purchasing.requests.convert"), exact: true }).click();
  await page.waitForURL(/#\/purchasing\/orders\/[0-9a-f-]{36}$/);
  const orderId = page.url().split("/").pop()!;
  const orderPath = `/purchasing/orders/${orderId}`;

  let order = await apiGet<PurchaseOrderApi>(orderPath);
  expect(order.subtotal_minor).toBe(1_600_000);
  expect(order.status).toBe("draft");

  // The converted order carries the same subtotal, so it needs its own Approve before Confirm.
  // Approving doesn't change the status badge (still "draft"), so confirm the `approved` flag.
  await page.getByRole("button", { name: t("purchasing.detail.approve"), exact: true }).click();
  await expect(async () => {
    expect((await apiGet<PurchaseOrderApi>(orderPath)).approved).toBe(true);
  }).toPass();
  await page.reload();

  await runStep<PurchaseOrderApi>(page, apiGet, orderPath, t("purchasing.detail.confirm"), "confirmed");
  await runStep<PurchaseOrderApi>(page, apiGet, orderPath, t("purchasing.detail.receive"), "received");

  // 3-way match: ordered 200 = received 200 = billed 200 @ 80.00 — no variance, no manual entry.
  await runStep<PurchaseOrderApi>(page, apiGet, orderPath, t("purchasing.detail.bill"), "billed");

  order = await apiGet<PurchaseOrderApi>(orderPath);
  expect(order.received_minor).toBe(1_600_000);
  expect(order.billed_minor).toBe(1_600_000);
  expect(order.outstanding_minor).toBe(1_600_000);

  // Partial payment (delivery-readiness FILE_05): order stays open with a reduced balance.
  await page.getByRole("button", { name: t("purchasing.detail.recordPayment"), exact: true }).click();
  await page.getByLabel(t("document.paymentDialog.amount")).fill("600.00");
  await page.getByRole("button", { name: t("document.paymentDialog.confirm"), exact: true }).click();

  await expect(async () => {
    order = await apiGet<PurchaseOrderApi>(orderPath);
    expect(order.paid_minor).toBe(60_000);
  }).toPass();
  expect(order.outstanding_minor).toBe(1_540_000);
  expect(order.status).toBe("billed");
  await page.reload();

  // Final payment (dialog defaults to the remaining outstanding) settles the order in full.
  await page.getByRole("button", { name: t("purchasing.detail.recordPayment"), exact: true }).click();
  await page.getByRole("button", { name: t("document.paymentDialog.confirm"), exact: true }).click();

  await expect(async () => {
    order = await apiGet<PurchaseOrderApi>(orderPath);
    expect(order.status).toBe("paid");
  }).toPass();
  expect(order.paid_minor).toBe(1_600_000);
  expect(order.outstanding_minor).toBe(0);
});
