import { Suspense, lazy } from "react";
import { HashRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { PeekProvider } from "./components/PeekCard";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { PreferencesProvider, usePreferences } from "./preferences/PreferencesContext";
import { getSetupStatus } from "./api/setup";
import { useAsync } from "./hooks/useAsync";
import { ListSkeleton } from "./components/ListSkeleton";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { ResolveRedirect } from "./app/ResolveRedirect";
import type { ReactNode } from "react";

// Heavy or rarely-visited screens load on demand so the main chunk stays inside the bundle
// budget (scripts/check-bundle-size.mjs): the workflow canvas carries React Flow, the report
// builder and setup wizard are big one-offs, and settings/admin are visited far less often
// than the transactional pages. Each lazy route falls back to the shared route skeleton.
const lazyPage = <T extends Record<string, any>>(load: () => Promise<T>, name: keyof T) =>
  lazy(() => load().then((m) => ({ default: m[name] })));

const SetupWizardPage = lazyPage(() => import("./pages/SetupWizardPage"), "SetupWizardPage");
const WorkflowCanvasPage = lazyPage(() => import("./pages/WorkflowCanvasPage"), "WorkflowCanvasPage");
const ReportBuilderPage = lazyPage(
  () => import("./pages/accounting/ReportBuilderPage"), "ReportBuilderPage");
const InvoiceDocumentPage = lazyPage(
  () => import("./pages/sales/InvoiceDocumentPage"), "InvoiceDocumentPage");
const ProfilePage = lazyPage(() => import("./pages/settings/ProfilePage"), "ProfilePage");
const AppearancePage = lazyPage(() => import("./pages/settings/AppearancePage"), "AppearancePage");
const DashboardSettingsPage = lazyPage(
  () => import("./pages/settings/DashboardSettingsPage"), "DashboardSettingsPage");
const NavigationSettingsPage = lazyPage(
  () => import("./pages/settings/NavigationSettingsPage"), "NavigationSettingsPage");
const NotificationsSettingsPage = lazyPage(
  () => import("./pages/settings/NotificationsSettingsPage"), "NotificationsSettingsPage");
const AccessibilityPage = lazyPage(
  () => import("./pages/settings/AccessibilityPage"), "AccessibilityPage");
const OrganizationPage = lazyPage(
  () => import("./pages/settings/OrganizationPage"), "OrganizationPage");
const BranchesPage = lazyPage(
  () => import("./pages/settings/BranchesPage"), "BranchesPage");
const WebhooksSettingsPage = lazyPage(
  () => import("./pages/settings/WebhooksSettingsPage"), "WebhooksSettingsPage");
const CustomFieldsPage = lazyPage(
  () => import("./pages/settings/CustomFieldsPage"), "CustomFieldsPage");
const ApiKeysPage = lazyPage(
  () => import("./pages/settings/ApiKeysPage"), "ApiKeysPage");
const EInvoicePage = lazyPage(
  () => import("./pages/settings/EInvoicePage"), "EInvoicePage");
const SystemPage = lazyPage(
  () => import("./pages/settings/SystemPage"), "SystemPage");
const AIUsagePage = lazyPage(
  () => import("./pages/settings/AIUsagePage"), "AIUsagePage");
const UsersPage = lazyPage(() => import("./pages/admin/UsersPage"), "UsersPage");
const UserDetailPage = lazyPage(() => import("./pages/admin/UserDetailPage"), "UserDetailPage");
const RolesPage = lazyPage(() => import("./pages/admin/RolesPage"), "RolesPage");
const AssistantPage = lazyPage(() => import("./pages/assistant/AssistantPage"), "AssistantPage");
const KnowledgePage = lazyPage(() => import("./pages/assistant/KnowledgePage"), "KnowledgePage");
const OpsPage = lazyPage(() => import("./pages/assistant/OpsPage"), "OpsPage");
const RoleDetailPage = lazyPage(() => import("./pages/admin/RoleDetailPage"), "RoleDetailPage");
const PipelinePage = lazyPage(() => import("./pages/crm/PipelinePage"), "PipelinePage");
const OpportunityDetailPage = lazyPage(
  () => import("./pages/crm/OpportunityDetailPage"), "OpportunityDetailPage");
const LeadsPage = lazyPage(() => import("./pages/crm/LeadsPage"), "LeadsPage");
const TicketsPage = lazyPage(() => import("./pages/crm/TicketsPage"), "TicketsPage");
const CampaignsPage = lazyPage(() => import("./pages/crm/CampaignsPage"), "CampaignsPage");
const CampaignDetailPage = lazyPage(
  () => import("./pages/crm/CampaignDetailPage"), "CampaignDetailPage");
const UserGuidePage = lazyPage(() => import("./pages/UserGuidePage"), "UserGuidePage");
const WorkflowListPage = lazyPage(() => import("./pages/WorkflowListPage"), "WorkflowListPage");
const InstanceListPage = lazyPage(() => import("./pages/InstanceListPage"), "InstanceListPage");
const ExecutionViewerPage = lazyPage(
  () => import("./pages/ExecutionViewerPage"), "ExecutionViewerPage");
const ChartOfAccountsPage = lazyPage(
  () => import("./pages/accounting/ChartOfAccountsPage"), "ChartOfAccountsPage");
const JournalListPage = lazyPage(
  () => import("./pages/accounting/JournalListPage"), "JournalListPage");
const JournalEntryPage = lazyPage(
  () => import("./pages/accounting/JournalEntryPage"), "JournalEntryPage");
const JournalDetailPage = lazyPage(
  () => import("./pages/accounting/JournalDetailPage"), "JournalDetailPage");
const TrialBalancePage = lazyPage(
  () => import("./pages/accounting/TrialBalancePage"), "TrialBalancePage");
const GeneralLedgerPage = lazyPage(
  () => import("./pages/accounting/GeneralLedgerPage"), "GeneralLedgerPage");
const IncomeStatementPage = lazyPage(
  () => import("./pages/accounting/IncomeStatementPage"), "IncomeStatementPage");
const BalanceSheetPage = lazyPage(
  () => import("./pages/accounting/BalanceSheetPage"), "BalanceSheetPage");
const CashFlowStatementPage = lazyPage(
  () => import("./pages/accounting/CashFlowStatementPage"), "CashFlowStatementPage");
const VatReturnPage = lazyPage(
  () => import("./pages/accounting/VatReturnPage"), "VatReturnPage");
const FixedAssetsPage = lazyPage(
  () => import("./pages/accounting/FixedAssetsPage"), "FixedAssetsPage");
const FixedAssetDetailPage = lazyPage(
  () => import("./pages/accounting/FixedAssetDetailPage"), "FixedAssetDetailPage");
const CostCentersPage = lazyPage(
  () => import("./pages/accounting/CostCentersPage"), "CostCentersPage");
const BankReconciliationPage = lazyPage(
  () => import("./pages/accounting/BankReconciliationPage"), "BankReconciliationPage");
const BankStatementDetailPage = lazyPage(
  () => import("./pages/accounting/BankStatementDetailPage"), "BankStatementDetailPage");
const BudgetsPage = lazyPage(() => import("./pages/accounting/BudgetsPage"), "BudgetsPage");
const BudgetDetailPage = lazyPage(
  () => import("./pages/accounting/BudgetDetailPage"), "BudgetDetailPage");
const EInvoicesPage = lazyPage(() => import("./pages/einvoice/EInvoicesPage"), "EInvoicesPage");
const NotificationsPage = lazyPage(
  () => import("./pages/notifications/NotificationsPage"), "NotificationsPage");
const StockOnHandPage = lazyPage(
  () => import("./pages/inventory/StockOnHandPage"), "StockOnHandPage");
const ItemsPage = lazyPage(() => import("./pages/inventory/ItemsPage"), "ItemsPage");
const ItemDetailPage = lazyPage(
  () => import("./pages/inventory/ItemDetailPage"), "ItemDetailPage");
const WarehousesPage = lazyPage(
  () => import("./pages/inventory/WarehousesPage"), "WarehousesPage");
const WarehouseDetailPage = lazyPage(
  () => import("./pages/inventory/WarehouseDetailPage"), "WarehouseDetailPage");
const PriceListsPage = lazyPage(() => import("./pages/pricing/PriceListsPage"), "PriceListsPage");
const PriceListDetailPage = lazyPage(
  () => import("./pages/pricing/PriceListDetailPage"), "PriceListDetailPage");
const CustomerPricingPage = lazyPage(
  () => import("./pages/pricing/CustomerPricingPage"), "CustomerPricingPage");
const StockMovementPage = lazyPage(
  () => import("./pages/inventory/StockMovementPage"), "StockMovementPage");
const StockCountsPage = lazyPage(
  () => import("./pages/inventory/StockCountsPage"), "StockCountsPage");
const StockCountDetailPage = lazyPage(
  () => import("./pages/inventory/StockCountDetailPage"), "StockCountDetailPage");
const BatchesPage = lazyPage(() => import("./pages/inventory/BatchesPage"), "BatchesPage");
const SupplierAliasesPage = lazyPage(
  () => import("./pages/inventory/SupplierAliasesPage"), "SupplierAliasesPage");
const OrdersPage = lazyPage(() => import("./pages/sales/OrdersPage"), "OrdersPage");
const NewOrderPage = lazyPage(() => import("./pages/sales/NewOrderPage"), "NewOrderPage");
const OrderDetailPage = lazyPage(
  () => import("./pages/sales/OrderDetailPage"), "OrderDetailPage");
const CustomersPage = lazyPage(() => import("./pages/sales/CustomersPage"), "CustomersPage");
const CustomerDetailPage = lazyPage(
  () => import("./pages/sales/CustomerDetailPage"), "CustomerDetailPage");
const QuotationsPage = lazyPage(
  () => import("./pages/sales/QuotationsPage"), "QuotationsPage");
const NewQuotationPage = lazyPage(
  () => import("./pages/sales/NewQuotationPage"), "NewQuotationPage");
const QuotationDetailPage = lazyPage(
  () => import("./pages/sales/QuotationDetailPage"), "QuotationDetailPage");
const PurchaseOrdersPage = lazyPage(
  () => import("./pages/purchasing/PurchaseOrdersPage"), "PurchaseOrdersPage");
const NewPurchaseOrderPage = lazyPage(
  () => import("./pages/purchasing/NewPurchaseOrderPage"), "NewPurchaseOrderPage");
const ImportInvoicePage = lazyPage(
  () => import("./pages/purchasing/ImportInvoicePage"), "ImportInvoicePage");
const PurchaseOrderDetailPage = lazyPage(
  () => import("./pages/purchasing/PurchaseOrderDetailPage"), "PurchaseOrderDetailPage");
const SuppliersPage = lazyPage(
  () => import("./pages/purchasing/SuppliersPage"), "SuppliersPage");
const SupplierDetailPage = lazyPage(
  () => import("./pages/purchasing/SupplierDetailPage"), "SupplierDetailPage");
const PurchaseRequestsPage = lazyPage(
  () => import("./pages/purchasing/PurchaseRequestsPage"), "PurchaseRequestsPage");
const NewPurchaseRequestPage = lazyPage(
  () => import("./pages/purchasing/NewPurchaseRequestPage"), "NewPurchaseRequestPage");
const PurchaseRequestDetailPage = lazyPage(
  () => import("./pages/purchasing/PurchaseRequestDetailPage"), "PurchaseRequestDetailPage");
const ImportWizard = lazyPage(() => import("./pages/imports/ImportWizard"), "ImportWizard");

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, restoring } = useAuth();
  if (restoring) return null; // boot-time cookie→token restore in flight — don't flash /login
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
      <Suspense fallback={<ListSkeleton rows={6} />}>
        <SetupWizardPage
          status={data}
          onCompleted={async () => {
            // Pull fresh org flags (e.g. e-invoicing) before entering the app so the nav is correct.
            await refresh();
            mutate({ ...data, is_setup_complete: true });
          }}
        />
      </Suspense>
    );
  }
  return <AppRoutes />;
}

function AppRoutes() {
  return (
    <PeekProvider>
      <AppShell>
        {/* Lazy routes paint the shared list skeleton inside the intact shell while their chunk
            loads — the same designed beat as a data load, never a blank screen or spinner. */}
        <Suspense fallback={<ListSkeleton rows={6} />}>
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
          <Route path="/settings/branches" element={<BranchesPage />} />
          <Route path="/settings/webhooks" element={<WebhooksSettingsPage />} />
          <Route path="/settings/custom-fields" element={<CustomFieldsPage />} />
          <Route path="/settings/developers" element={<ApiKeysPage />} />
          <Route path="/settings/einvoice" element={<EInvoicePage />} />
          <Route path="/settings/system" element={<SystemPage />} />
          <Route path="/imports/:id" element={<ImportWizard />} />
          <Route path="/settings/ai-usage" element={<AIUsagePage />} />
          <Route path="/admin/users" element={<UsersPage />} />
          <Route path="/admin/users/:id" element={<UserDetailPage />} />
          <Route path="/admin/roles" element={<RolesPage />} />
          <Route path="/admin/roles/:name" element={<RoleDetailPage />} />
          <Route path="/pricing" element={<PriceListsPage />} />
          <Route path="/pricing/customers" element={<CustomerPricingPage />} />
          <Route path="/pricing/:id" element={<PriceListDetailPage />} />
          <Route path="/workflows" element={<WorkflowListPage />} />
          <Route path="/workflows/instances" element={<InstanceListPage />} />
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
          <Route path="/inventory/supplier-aliases" element={<SupplierAliasesPage />} />
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
          <Route path="/purchasing/orders/import" element={<ImportInvoicePage />} />
          <Route path="/purchasing/orders/:id" element={<PurchaseOrderDetailPage />} />
          <Route path="/purchasing/requests" element={<PurchaseRequestsPage />} />
          <Route path="/purchasing/requests/new" element={<NewPurchaseRequestPage />} />
          <Route path="/purchasing/requests/:id" element={<PurchaseRequestDetailPage />} />
          <Route path="/purchasing/suppliers" element={<SuppliersPage />} />
          <Route path="/purchasing/suppliers/:code" element={<SupplierDetailPage />} />
          <Route path="/einvoice" element={<EInvoicesPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/assistant/knowledge" element={<KnowledgePage />} />
          <Route path="/assistant/ops" element={<OpsPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/help/guide" element={<UserGuidePage />} />
          <Route path="/help/guide/:journeyId" element={<UserGuidePage />} />
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
        </Suspense>
      </AppShell>
    </PeekProvider>
  );
}

export default function App() {
  return (
    <AppErrorBoundary>
      <AuthProvider>
        <HashRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/*" element={<Protected />} />
          </Routes>
        </HashRouter>
      </AuthProvider>
    </AppErrorBoundary>
  );
}
