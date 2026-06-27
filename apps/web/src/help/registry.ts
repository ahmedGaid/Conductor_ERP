// Route -> help guide registry.
//
// Every route in App.tsx must have an entry here — gate03 fails the build otherwise, which is how
// help stays in sync as the app grows: add a page, you're forced to add its guide. Some routes share
// a guide (e.g. /crm and /crm/pipeline are the same screen).
//
// `resolveGuide` matches the current path against these patterns, trying the most specific first so
// that, say, "/sales/orders/new" wins over "/sales/orders/:id".
import { matchPath } from "react-router-dom";

import type { HelpGuide } from "./types";
import {
  dashboardGuide,
  einvoiceGuide,
  executionViewerGuide,
  notificationsGuide,
  workflowCanvasGuide,
  workflowsGuide,
} from "./content/platform";
import {
  balanceSheetGuide,
  bankReconciliationGuide,
  bankStatementDetailGuide,
  budgetDetailGuide,
  budgetsGuide,
  cashFlowGuide,
  chartOfAccountsGuide,
  costCentersGuide,
  fixedAssetDetailGuide,
  fixedAssetsGuide,
  generalLedgerGuide,
  incomeStatementGuide,
  journalDetailGuide,
  journalEntryGuide,
  journalListGuide,
  reportBuilderGuide,
  trialBalanceGuide,
  vatReturnGuide,
} from "./content/accounting";
import {
  batchesGuide,
  itemsGuide,
  stockCountDetailGuide,
  stockCountsGuide,
  stockMovementGuide,
  stockOnHandGuide,
  warehousesGuide,
} from "./content/inventory";
import {
  customersGuide,
  newOrderGuide,
  newQuotationGuide,
  orderDetailGuide,
  ordersGuide,
  quotationDetailGuide,
  quotationsGuide,
} from "./content/sales";
import {
  newPurchaseOrderGuide,
  newPurchaseRequestGuide,
  purchaseOrderDetailGuide,
  purchaseOrdersGuide,
  purchaseRequestDetailGuide,
  purchaseRequestsGuide,
  suppliersGuide,
} from "./content/purchasing";
import {
  campaignDetailGuide,
  campaignsGuide,
  leadsGuide,
  opportunityDetailGuide,
  pipelineGuide,
  ticketsGuide,
} from "./content/crm";
import {
  settingsAccessibilityGuide,
  settingsAppearanceGuide,
  settingsDashboardGuide,
  settingsNavigationGuide,
  settingsNotificationsGuide,
  settingsOrganizationGuide,
  settingsProfileGuide,
} from "./content/settings";
import { roleDetailGuide, rolesGuide, userDetailGuide, usersGuide } from "./content/admin";
import { priceListDetailGuide, priceListsGuide } from "./content/pricing";

export const HELP_GUIDES: Record<string, HelpGuide> = {
  "/": dashboardGuide,
  "/workflows": workflowsGuide,
  "/workflows/new": workflowCanvasGuide,
  "/workflows/:id": workflowCanvasGuide,
  "/instances/:id": executionViewerGuide,
  "/accounting": chartOfAccountsGuide,
  "/accounting/journals": journalListGuide,
  "/accounting/journals/new": journalEntryGuide,
  "/accounting/journals/:id": journalDetailGuide,
  "/accounting/trial-balance": trialBalanceGuide,
  "/accounting/general-ledger": generalLedgerGuide,
  "/accounting/income-statement": incomeStatementGuide,
  "/accounting/balance-sheet": balanceSheetGuide,
  "/accounting/cash-flow": cashFlowGuide,
  "/accounting/vat-return": vatReturnGuide,
  "/accounting/assets": fixedAssetsGuide,
  "/accounting/assets/:code": fixedAssetDetailGuide,
  "/accounting/cost-centers": costCentersGuide,
  "/accounting/bank-reconciliation": bankReconciliationGuide,
  "/accounting/bank-reconciliation/:id": bankStatementDetailGuide,
  "/accounting/budgets": budgetsGuide,
  "/accounting/budgets/:id": budgetDetailGuide,
  "/accounting/report-builder": reportBuilderGuide,
  "/inventory": stockOnHandGuide,
  "/inventory/items": itemsGuide,
  "/inventory/warehouses": warehousesGuide,
  "/inventory/movements": stockMovementGuide,
  "/inventory/stock-on-hand": stockOnHandGuide,
  "/inventory/counts": stockCountsGuide,
  "/inventory/counts/:id": stockCountDetailGuide,
  "/inventory/batches": batchesGuide,
  "/sales": ordersGuide,
  "/sales/orders/new": newOrderGuide,
  "/sales/orders/:id": orderDetailGuide,
  "/sales/quotations": quotationsGuide,
  "/sales/quotations/new": newQuotationGuide,
  "/sales/quotations/:id": quotationDetailGuide,
  "/sales/customers": customersGuide,
  "/purchasing": purchaseOrdersGuide,
  "/purchasing/orders/new": newPurchaseOrderGuide,
  "/purchasing/orders/:id": purchaseOrderDetailGuide,
  "/purchasing/requests": purchaseRequestsGuide,
  "/purchasing/requests/new": newPurchaseRequestGuide,
  "/purchasing/requests/:id": purchaseRequestDetailGuide,
  "/purchasing/suppliers": suppliersGuide,
  "/einvoice": einvoiceGuide,
  "/notifications": notificationsGuide,
  "/crm": pipelineGuide,
  "/crm/pipeline": pipelineGuide,
  "/crm/opportunities/:id": opportunityDetailGuide,
  "/crm/leads": leadsGuide,
  "/crm/tickets": ticketsGuide,
  "/crm/campaigns": campaignsGuide,
  "/crm/campaigns/:id": campaignDetailGuide,
  "/settings": settingsProfileGuide,
  "/settings/profile": settingsProfileGuide,
  "/settings/appearance": settingsAppearanceGuide,
  "/settings/dashboard": settingsDashboardGuide,
  "/settings/navigation": settingsNavigationGuide,
  "/settings/notifications": settingsNotificationsGuide,
  "/settings/accessibility": settingsAccessibilityGuide,
  "/settings/organization": settingsOrganizationGuide,
  "/admin/users": usersGuide,
  "/admin/users/:id": userDetailGuide,
  "/admin/roles": rolesGuide,
  "/admin/roles/:name": roleDetailGuide,
  "/pricing": priceListsGuide,
  "/pricing/:id": priceListDetailGuide,
};

// Pre-sort patterns most-specific first: deeper paths first, and within the same depth, patterns
// with fewer URL params (more literal segments) first — so a static route beats a param route.
const SORTED_PATTERNS = Object.keys(HELP_GUIDES).sort((a, b) => {
  const depth = (p: string) => p.split("/").length;
  const params = (p: string) => (p.match(/:/g) ?? []).length;
  return depth(b) - depth(a) || params(a) - params(b);
});

export function resolveGuide(pathname: string): HelpGuide | undefined {
  for (const pattern of SORTED_PATTERNS) {
    if (matchPath(pattern, pathname)) return HELP_GUIDES[pattern];
  }
  return undefined;
}
