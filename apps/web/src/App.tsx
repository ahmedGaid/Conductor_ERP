import { HashRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
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
import { EInvoicesPage } from "./pages/einvoice/EInvoicesPage";
import { StockOnHandPage } from "./pages/inventory/StockOnHandPage";
import { ItemsPage } from "./pages/inventory/ItemsPage";
import { WarehousesPage } from "./pages/inventory/WarehousesPage";
import { StockMovementPage } from "./pages/inventory/StockMovementPage";
import { OrdersPage } from "./pages/sales/OrdersPage";
import { NewOrderPage } from "./pages/sales/NewOrderPage";
import { OrderDetailPage } from "./pages/sales/OrderDetailPage";
import { CustomersPage } from "./pages/sales/CustomersPage";
import { QuotationsPage } from "./pages/sales/QuotationsPage";
import { NewQuotationPage } from "./pages/sales/NewQuotationPage";
import { QuotationDetailPage } from "./pages/sales/QuotationDetailPage";
import { PurchaseOrdersPage } from "./pages/purchasing/PurchaseOrdersPage";
import { NewPurchaseOrderPage } from "./pages/purchasing/NewPurchaseOrderPage";
import { PurchaseOrderDetailPage } from "./pages/purchasing/PurchaseOrderDetailPage";
import { SuppliersPage } from "./pages/purchasing/SuppliersPage";
import { PurchaseRequestsPage } from "./pages/purchasing/PurchaseRequestsPage";
import { NewPurchaseRequestPage } from "./pages/purchasing/NewPurchaseRequestPage";
import { PurchaseRequestDetailPage } from "./pages/purchasing/PurchaseRequestDetailPage";
import { PipelinePage } from "./pages/crm/PipelinePage";
import { OpportunityDetailPage } from "./pages/crm/OpportunityDetailPage";
import { LeadsPage } from "./pages/crm/LeadsPage";
import { TicketsPage } from "./pages/crm/TicketsPage";
import type { ReactNode } from "react";

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Protected() {
  return (
    <RequireAuth>
      <AppShell>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
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
          <Route path="/inventory" element={<StockOnHandPage />} />
          <Route path="/inventory/items" element={<ItemsPage />} />
          <Route path="/inventory/warehouses" element={<WarehousesPage />} />
          <Route path="/inventory/movements" element={<StockMovementPage />} />
          <Route path="/inventory/stock-on-hand" element={<StockOnHandPage />} />
          <Route path="/sales" element={<OrdersPage />} />
          <Route path="/sales/orders/new" element={<NewOrderPage />} />
          <Route path="/sales/orders/:id" element={<OrderDetailPage />} />
          <Route path="/sales/quotations" element={<QuotationsPage />} />
          <Route path="/sales/quotations/new" element={<NewQuotationPage />} />
          <Route path="/sales/quotations/:id" element={<QuotationDetailPage />} />
          <Route path="/sales/customers" element={<CustomersPage />} />
          <Route path="/purchasing" element={<PurchaseOrdersPage />} />
          <Route path="/purchasing/orders/new" element={<NewPurchaseOrderPage />} />
          <Route path="/purchasing/orders/:id" element={<PurchaseOrderDetailPage />} />
          <Route path="/purchasing/requests" element={<PurchaseRequestsPage />} />
          <Route path="/purchasing/requests/new" element={<NewPurchaseRequestPage />} />
          <Route path="/purchasing/requests/:id" element={<PurchaseRequestDetailPage />} />
          <Route path="/purchasing/suppliers" element={<SuppliersPage />} />
          <Route path="/einvoice" element={<EInvoicesPage />} />
          <Route path="/crm" element={<PipelinePage />} />
          <Route path="/crm/pipeline" element={<PipelinePage />} />
          <Route path="/crm/opportunities/:id" element={<OpportunityDetailPage />} />
          <Route path="/crm/leads" element={<LeadsPage />} />
          <Route path="/crm/tickets" element={<TicketsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </RequireAuth>
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
