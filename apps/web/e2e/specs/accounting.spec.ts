import { test, expect } from "../lib/fixtures";

// Prerequisite: `manage.py seed_accounting` (chart of accounts incl. postable accounts 1000 Cash
// and 6100 Bank Charges) — see Docs/RUNBOOK.md "Regression run before every release".
interface TrialBalanceApi {
  total_debit: number;
  total_credit: number;
  is_balanced: boolean;
}

test("accounting: a balanced manual journal posts and the trial balance still balances", async ({
  page,
  t,
  apiGet,
}) => {
  const before = await apiGet<TrialBalanceApi>("/accounting/reports/trial-balance");
  expect(before.is_balanced).toBe(true);
  expect(before.total_debit).toBe(before.total_credit);

  await page.goto("/#/accounting/journals/new");

  const rows = page.locator(".acct-table tbody tr");
  await rows.nth(0).locator("select").nth(0).selectOption("6100"); // Bank Charges
  await rows.nth(0).locator("input").nth(0).fill("15.00"); // debit
  await rows.nth(1).locator("select").nth(0).selectOption("1000"); // Cash
  await rows.nth(1).locator("input").nth(1).fill("15.00"); // credit

  await expect(page.getByText(t("accounting.entry.balanced"), { exact: true })).toBeVisible();

  await page.getByRole("button", { name: t("accounting.entry.post") }).click();
  await page.waitForURL(/#\/accounting\/journals\/[0-9a-f-]{36}$/);

  // total_debit/total_credit are raw sums of posted debit/credit lines (see
  // erp/accounting/services/reports.py trial_balance), so one more balanced entry raises both by
  // the same 15.00 — Dr and Cr never drift apart.
  const after = await apiGet<TrialBalanceApi>("/accounting/reports/trial-balance");
  expect(after.is_balanced).toBe(true);
  expect(after.total_debit).toBe(after.total_credit);
  expect(after.total_debit).toBe(before.total_debit + 1_500);
  expect(after.total_credit).toBe(before.total_credit + 1_500);

  await page.goto("/#/accounting/trial-balance");
  await expect(page.getByText(t("accounting.entry.balanced"), { exact: true })).toBeVisible();
});
