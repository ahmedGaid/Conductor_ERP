import { HashRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { PreferencesProvider, usePreferences } from "./preferences/PreferencesContext";
import { getSetupStatus } from "./api/setup";
import { useAsync } from "./hooks/useAsync";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { SetupWizardPage } from "./pages/SetupWizardPage";
import { ProfilePage } from "./pages/settings/ProfilePage";
import { AppearancePage } from "./pages/settings/AppearancePage";
import { DashboardSettingsPage } from "./pages/settings/DashboardSettingsPage";
import { NavigationSettingsPage } from "./pages/settings/NavigationSettingsPage";
import { NotificationsSettingsPage } from "./pages/settings/NotificationsSettingsPage";
import { AccessibilityPage } from "./pages/settings/AccessibilityPage";
import { OrganizationPage } from "./pages/settings/OrganizationPage";
import { UsersPage } from "./pages/admin/UsersPage";
import { UserDetailPage } from "./pages/admin/UserDetailPage";
import { RolesPage } from "./pages/admin/RolesPage";
import { RoleDetailPage } from "./pages/admin/RoleDetailPage";
import { WorkflowListPage } from "./pages/WorkflowListPage";
import { WorkflowCanvasPage } from "./pages/WorkflowCanvasPage";
import { ExecutionViewerPage } from "./pages/ExecutionViewerPage";
import { ChartOfAccountsPage } from "./pages/accounting/ChartOfAccountsPage";
import { JournalListPage } from "./pages/accounting/JournalListPage";
import { JournalEntryPage } from "./pages/accounting/JournalEntryPage";
import { JournalDetailPage } from "./pages/accounting/JournalDetailPage";
import { TrialBalancePage } from "./pages/accounting/TrialBalancePage";
import { GeneralLedgerPage } from "./pages/accounting/GeneralLedgerPage";
import { IncomeStatementPage } from "./pages/accounting/IncomeStatementPage";
import { BalanceSheetPage } from "./pages/accounting/BalanceSheetPage";
import { CashFlowStatementPage } from "./pages/accounting/CashFlowStatementPage";
import { VatReturnPage } from "./pages/accounting/VatReturnPage";
import { FixedAssetsPage } from "./pages/accounting/FixedAssetsPage";
import { FixedAssetDetailPage } from "./pages/accounting/FixedAssetDetailPage";
import { CostCentersPage } from "./pages/accounting/CostCentersPage";
import { BankReconciliationPage } from "./pages/accounting/BankReconciliationPage";
import { BankStatementDetailPage } from "./pages/accounting/BankStatementDetailPage";
import { BudgetsPage } from "./pages/accounting/BudgetsPage";
import { BudgetDetailPage } from "./pages/accounting/BudgetDetailPage";
import { ReportBuilderPage } from "./pages/accounting/ReportBuilderPage";
import { EInvoicesPage } from "./pages/einvoice/EInvoicesPage";
import { NotificationsPage } from "./pages/notifications/NotificationsPage";
import { StockOnHandPage } from "./pages/inventory/StockOnHandPage";
import { ItemsPage } from "./pages/inventory/ItemsPage";
import { ItemDetailPage } from "./pages/inventory/ItemDetailPage";
import { WarehousesPage } from "./pages/inventory/WarehousesPage";
import { WarehouseDetailPage } from "./pages/inventory/WarehouseDetailPage";
import { ResolveRedirect } from "./app/ResolveRedirect";
import { PriceListsPage } from "./pages/pricing/PriceListsPage";
import { PriceListDetailPage } from "./pages/pricing/PriceListDetailPage";
import { CustomerPricingPage } from "./pages/pricing/CustomerPricingPage";
import { StockMovementPage } from "./pages/inventory/StockMovementPage";
import { StockCountsPage } from "./pages/inventory/StockCountsPage";
import { StockCountDetailPage } from "./pages/inventory/StockCountDetailPage";
import { BatchesPage } from "./pages/inventory/BatchesPage";
import { OrdersPage } from "./pages/sales/OrdersPage";
import { NewOrderPage } from "./pages/sales/NewOrderPage";
import { OrderDetailPage } from "./pages/sales/OrderDetailPage";
import { InvoiceDocumentPage } from "./pages/sales/InvoiceDocumentPage";
import { CustomersPage } from "./pages/sales/CustomersPage";
import { CustomerDetailPage } from "./pages/sales/CustomerDetailPage";
import { QuotationsPage } from "./pages/sales/QuotationsPage";
import { NewQuotationPage } from "./pages/sales/NewQuotationPage";
import { QuotationDetailPage } from "./pages/sales/QuotationDetailPage";
import { PurchaseOrdersPage } from "./pages/purchasing/PurchaseOrdersPage";
import { NewPurchaseOrderPage } from "./pages/purchasing/NewPurchaseOrderPage";
import { PurchaseOrderDetailPage } from "./pages/purchasing/PurchaseOrderDetailPage";
import { SuppliersPage } from "./pages/purchasing/SuppliersPage";
import { SupplierDetailPage } from "./pages/purchasing/SupplierDetailPage";
import { PurchaseRequestsPage } from "./pages/purchasing/PurchaseRequestsPage";
import { NewPurchaseRequestPage } from "./pages/purchasing/NewPurchaseRequestPage";
import { PurchaseRequestDetailPage } from "./pages/purchasing/PurchaseRequestDetailPage";
import { PipelinePage } from "./pages/crm/PipelinePage";
import { OpportunityDetailPage } from "./pages/crm/OpportunityDetailPage";
import { LeadsPage } from "./pages/crm/LeadsPage";
import { TicketsPage } from "./pages/crm/TicketsPage";
import { CampaignsPage } from "./pages/crm/CampaignsPage";
import { CampaignDetailPage } from "./pages/crm/CampaignDetailPage";
import type { ReactNode } from "react";

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// Land the user on their chosen page right after login — but only once per session, so the
// Dashboard stays reachable at "/" afterwards (no redirect loop). Defaults to the Dashboard.
function LandingRedirect() {
  const { prefs } = usePreferences();
  const target = prefs?.default_landing;
  if (prefs && !sessionStorage.getItem("erp.landingApplied")) {
    sessionStorage.setItem("erp.landingApplied", "1");
    if (target && target !== "/") return <Navigate to={target} replace />;
  }
  return <DashboardPage />;
}

function Protected() {
  return (
    <RequireAuth>
      <PreferencesProvider>
        <SetupGate />
      </PreferencesProvider>
    </RequireAuth>
  );
}

// First-run gate: until the org finishes setup, every protected route funnels to the wizard;
// once complete, the wizard is unreachable (redirects home). Auth already passed by here.
function SetupGate() {
  const { data, loading, mutate } = useAsync(getSetupStatus, []);
  const { refresh } = usePreferences();
  const location = useLocation();
  const onSetup = location.pathname === "/setup";

  if (loading || !data) return null;
  if (!data.is_setup_complete && !onSetup) return <Navigate to="/setup" replace />;
  if (data.is_setup_complete && onSetup) return <Navigate to="/" replace />;
  if (onSetup) {
    return (
      <SetupWizardPage
        status={data}
        onCompleted={async () => {
          // Pull fresh org flags (e.g. e-invoicing) before entering the app so the nav is correct.
          await refresh();
          mutate({ ...data, is_setup_complete: true });
        }}
      />
    );
  }
  return <AppRoutes />;
}

function AppRoutes() {
  return (
      <AppShell>
        <Routes>
          <Route path="/" element={<LandingRedirect />} />
          <Route path="/settings" element={<Navigate to="/settings/profile" replace />} />
          <Route path="/settings/profile" element={<ProfilePage />} />
          <Route path="/settings/appearance" element={<AppearancePage />} />
          <Route path="/settings/dashboard" element={<DashboardSettingsPage />} />
          <Route path="/settings/navigation" element={<NavigationSettingsPage />} />
          <Route path="/settings/notifications" element={<NotificationsSettingsPage />} />
          <Route path="/settings/accessibility" element={<AccessibilityPage />} />
          <Route path="/settings/organization" element={<OrganizationPage />} />
          <Route path="/admin/users" element={<UsersPage />} />
          <Route path="/admin/users/:id" element={<UserDetailPage />} />
          <Route path="/admin/roles" element={<RolesPage />} />
          <Route path="/admin/roles/:name" element={<RoleDetailPage />} />
          <Route path="/pricing" element={<PriceListsPage />} />
          <Route path="/pricing/customers" element={<CustomerPricingPage />} />
          <Route path="/pricing/:id" element={<PriceListDetailPage />} />
          <Route path="/workflows" element={<WorkflowListPage />} />
          <Route path="/workflows/new" element={<WorkflowCanvasPage />} />
          <Route path="/workflows/:id" element={<WorkflowCanvasPage />} />
          <Route path="/instances/:id" element={<ExecutionViewerPage />} />
          <Route path="/accounting" element={<ChartOfAccountsPage />} />
          <Route path="/accounting/journals" element={<JournalListPage />} />
          <Route path="/accounting/journals/new" element={<JournalEntryPage />} />
          <Route path="/accounting/journals/:id" element={<JournalDetailPage />} />
          <Route path="/accounting/trial-balance" element={<TrialBalancePage />} />
          <Route path="/accounting/general-ledger" element={<GeneralLedgerPage />} />
          <Route path="/accounting/income-statement" element={<IncomeStatementPage />} />
          <Route path="/accounting/balance-sheet" element={<BalanceSheetPage />} />
          <Route path="/accounting/cash-flow" element={<CashFlowStatementPage />} />
          <Route path="/accounting/vat-return" element={<VatReturnPage />} />
          <Route path="/accounting/assets" element={<FixedAssetsPage />} />
          <Route path="/accounting/assets/:code" element={<FixedAssetDetailPage />} />
          <Route path="/accounting/cost-centers" element={<CostCentersPage />} />
          <Route path="/accounting/bank-reconciliation" element={<BankReconciliationPage />} />
          <Route path="/accounting/bank-reconciliation/:id" element={<BankStatementDetailPage />} />
          <Route path="/accounting/budgets" element={<BudgetsPage />} />
          <Route path="/accounting/budgets/:id" element={<BudgetDetailPage />} />
          <Route path="/accounting/report-builder" element={<ReportBuilderPage />} />
          <Route path="/inventory" element={<StockOnHandPage />} />
          <Route path="/inventory/items" element={<ItemsPage />} />
          <Route path="/inventory/items/:sku" element={<ItemDetailPage />} />
          <Route path="/inventory/warehouses" element={<WarehousesPage />} />
          <Route path="/inventory/warehouses/:code" element={<WarehouseDetailPage />} />
          <Route path="/inventory/movements" element={<StockMovementPage />} />
          <Route path="/inventory/stock-on-hand" element={<StockOnHandPage />} />
          <Route path="/inventory/counts" element={<StockCountsPage />} />
          <Route path="/inventory/counts/:id" element={<StockCountDetailPage />} />
          <Route path="/inventory/batches" element={<BatchesPage />} />
          <Route path="/sales" element={<OrdersPage />} />
          <Route path="/sales/orders/new" element={<NewOrderPage />} />
          <Route path="/sales/orders/:id" element={<OrderDetailPage />} />
          <Route path="/sales/orders/:id/invoice" element={<InvoiceDocumentPage />} />
          <Route path="/sales/quotations" element={<QuotationsPage />} />
          <Route path="/sales/quotations/new" element={<NewQuotationPage />} />
          <Route path="/sales/quotations/:id" element={<QuotationDetailPage />} />
          <Route path="/sales/customers" element={<CustomersPage />} />
          <Route path="/sales/customers/:code" element={<CustomerDetailPage />} />
          <Route path="/purchasing" element={<PurchaseOrdersPage />} />
          <Route path="/purchasing/orders/new" element={<NewPurchaseOrderPage />} />
          <Route path="/purchasing/orders/:id" element={<PurchaseOrderDetailPage />} />
          <Route path="/purchasing/requests" element={<PurchaseRequestsPage />} />
          <Route path="/purchasing/requests/new" element={<NewPurchaseRequestPage />} />
          <Route path="/purchasing/requests/:id" element={<PurchaseRequestDetailPage />} />
          <Route path="/purchasing/suppliers" element={<SuppliersPage />} />
          <Route path="/purchasing/suppliers/:code" element={<SupplierDetailPage />} />
          <Route path="/einvoice" element={<EInvoicesPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          {/* Universal entity links resolve a business number → its UUID detail route. */}
          <Route path="/go/:type/:key" element={<ResolveRedirect />} />
          <Route path="/crm" element={<PipelinePage />} />
          <Route path="/crm/pipeline" element={<PipelinePage />} />
          <Route path="/crm/opportunities/:id" element={<OpportunityDetailPage />} />
          <Route path="/crm/leads" element={<LeadsPage />} />
          <Route path="/crm/tickets" element={<TicketsPage />} />
          <Route path="/crm/campaigns" element={<CampaignsPage />} />
          <Route path="/crm/campaigns/:id" element={<CampaignDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={<Protected />} />
        </Routes>
      </HashRouter>
    </AuthProvider>
  );
}
