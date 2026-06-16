// Typed wrappers for the accounting API (/api/accounting/*). Amounts are integer minor units.
import { apiFetch } from "./client";

export type AccountType = "asset" | "liability" | "equity" | "income" | "expense";
export type PeriodStatus = "open" | "closed";

export interface Account {
  id: string;
  code: string;
  name: string;
  type: AccountType;
  parent_code: string | null;
  is_postable: boolean;
  is_active: boolean;
  is_cash: boolean;
  currency: string;
}

export interface Period {
  id: string;
  fiscal_year_code: string;
  code: string;
  start_date: string;
  end_date: string;
  status: PeriodStatus;
}

export interface JournalLineInput {
  account_code: string;
  debit: number;
  credit: number;
  memo?: string;
  cost_center_code?: string;
}

export interface JournalLine {
  line_no: number;
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
  memo: string;
  cost_center_code: string;
}

export interface CostCenter {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface JournalEntry {
  id: string;
  number: string;
  date: string;
  period_code: string;
  currency: string;
  memo: string;
  reference: string;
  source: string;
  status: string;
  posted_at: string | null;
  lines: JournalLine[];
}

export interface TrialBalanceRow {
  account_code: string;
  account_name: string;
  account_type: AccountType;
  debit: number;
  credit: number;
  balance: number;
}

export interface TrialBalanceReport {
  rows: TrialBalanceRow[];
  total_debit: number;
  total_credit: number;
  is_balanced: boolean;
}

export interface LedgerLine {
  date: string;
  entry_number: string;
  memo: string;
  debit: number;
  credit: number;
  running_balance: number;
}

export interface GeneralLedgerReport {
  account_code: string;
  account_name: string;
  account_type: AccountType;
  opening_balance: number;
  closing_balance: number;
  lines: LedgerLine[];
}

export function listAccounts(): Promise<Account[]> {
  return apiFetch<Account[]>("/accounting/accounts");
}

export function createAccount(payload: {
  code: string;
  name: string;
  type: AccountType;
  parent_code?: string | null;
  is_postable?: boolean;
}): Promise<Account> {
  return apiFetch<Account>("/accounting/accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listPeriods(): Promise<Period[]> {
  return apiFetch<Period[]>("/accounting/periods");
}

export interface PostJournalPayload {
  date: string;
  memo?: string;
  reference?: string;
  period_code?: string | null;
  lines: JournalLineInput[];
}

export function postJournal(payload: PostJournalPayload): Promise<JournalEntry> {
  return apiFetch<JournalEntry>("/accounting/journals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listJournals(period?: string): Promise<JournalEntry[]> {
  const qs = period ? `?period=${encodeURIComponent(period)}` : "";
  return apiFetch<JournalEntry[]>(`/accounting/journals${qs}`);
}

export function getJournal(id: string): Promise<JournalEntry> {
  return apiFetch<JournalEntry>(`/accounting/journals/${id}`);
}

export function trialBalance(period?: string): Promise<TrialBalanceReport> {
  const qs = period ? `?period=${encodeURIComponent(period)}` : "";
  return apiFetch<TrialBalanceReport>(`/accounting/reports/trial-balance${qs}`);
}

export function generalLedger(account: string, period?: string): Promise<GeneralLedgerReport> {
  const q = new URLSearchParams({ account });
  if (period) q.set("period", period);
  return apiFetch<GeneralLedgerReport>(`/accounting/reports/general-ledger?${q.toString()}`);
}

// ---- Financial statements ----

export interface StatementLine {
  account_code: string;
  account_name: string;
  amount: number;
}

export interface IncomeStatementReport {
  date_from: string | null;
  date_to: string | null;
  cost_center: string | null;
  revenue: StatementLine[];
  expenses: StatementLine[];
  total_revenue: number;
  total_expenses: number;
  net_income: number;
}

export interface BalanceSheetReport {
  as_of: string | null;
  assets: StatementLine[];
  liabilities: StatementLine[];
  equity: StatementLine[];
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
  net_income: number;
  total_liabilities_and_equity: number;
  is_balanced: boolean;
}

export interface CashFlowReport {
  date_from: string | null;
  date_to: string | null;
  opening_balance: number;
  cash_in: number;
  cash_out: number;
  net_change: number;
  closing_balance: number;
  reconciles: boolean;
}

interface RangeParams {
  from?: string;
  to?: string;
  period?: string;
  cost_center?: string;
}

function rangeQuery(params: RangeParams): string {
  const q = new URLSearchParams();
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  if (params.period) q.set("period", params.period);
  if (params.cost_center) q.set("cost_center", params.cost_center);
  const s = q.toString();
  return s ? `?${s}` : "";
}

export function incomeStatement(params: RangeParams = {}): Promise<IncomeStatementReport> {
  return apiFetch<IncomeStatementReport>(`/accounting/reports/income-statement${rangeQuery(params)}`);
}

export function balanceSheet(asOf?: string): Promise<BalanceSheetReport> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return apiFetch<BalanceSheetReport>(`/accounting/reports/balance-sheet${qs}`);
}

export function cashFlow(params: RangeParams = {}): Promise<CashFlowReport> {
  return apiFetch<CashFlowReport>(`/accounting/reports/cash-flow${rangeQuery(params)}`);
}

// ---- Tax (VAT) ----

export interface TaxCode {
  code: string;
  name: string;
  rate_bps: number;
  output_account_code: string;
  input_account_code: string;
}

export interface VatReturnReport {
  start_date: string;
  end_date: string;
  output_vat: number;
  reversals: number;
  input_vat: number;
  input_reversals: number;
  net_payable: number;
  is_payable: boolean;
}

export function listTaxCodes(): Promise<TaxCode[]> {
  return apiFetch<TaxCode[]>("/accounting/tax-codes");
}

// ---- Cost centers (reporting dimension) ----

export function listCostCenters(): Promise<CostCenter[]> {
  return apiFetch<CostCenter[]>("/accounting/cost-centers");
}

export function createCostCenter(payload: { code: string; name: string }): Promise<CostCenter> {
  return apiFetch<CostCenter>("/accounting/cost-centers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---- Budgets ----

export interface Budget {
  id: string;
  name: string;
  fiscal_year_code: string;
  is_active: boolean;
}

export interface BudgetLineRow {
  account_code: string;
  period_code: string;
  amount_minor: number;
}

export interface BudgetDetail extends Budget {
  lines: BudgetLineRow[];
}

export interface VarianceRow {
  account_code: string;
  account_name: string;
  account_type: AccountType;
  budget_minor: number;
  actual_minor: number;
  variance_minor: number;
}

export interface BudgetVsActualReport {
  budget_id: string;
  budget_name: string;
  fiscal_year_code: string;
  period_code: string | null;
  rows: VarianceRow[];
  total_budget: number;
  total_actual: number;
  total_variance: number;
}

export function listBudgets(): Promise<Budget[]> {
  return apiFetch<Budget[]>("/accounting/budgets");
}

export function createBudget(payload: { name: string; fiscal_year_code: string }): Promise<Budget> {
  return apiFetch<Budget>("/accounting/budgets", { method: "POST", body: JSON.stringify(payload) });
}

export function getBudget(id: string): Promise<BudgetDetail> {
  return apiFetch<BudgetDetail>(`/accounting/budgets/${id}`);
}

export function setBudgetLine(id: string, payload: {
  account_code: string;
  period_code: string;
  amount_minor: number;
}): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/accounting/budgets/${id}/lines`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function budgetVsActual(id: string, period?: string): Promise<BudgetVsActualReport> {
  const qs = period ? `?period=${encodeURIComponent(period)}` : "";
  return apiFetch<BudgetVsActualReport>(`/accounting/budgets/${id}/variance${qs}`);
}

// ---- Bank reconciliation ----

export type BankStatementStatus = "open" | "reconciled";

export interface BankStatementLine {
  id: string;
  line_no: number;
  date: string;
  description: string;
  amount_minor: number;
  is_matched: boolean;
  matched_line_id: number | null;
}

export interface GLCandidate {
  id: number;
  date: string;
  entry_number: string;
  memo: string;
  amount_minor: number;
}

export interface ReconciliationSummary {
  book_balance: number;
  statement_closing: number;
  difference: number;
  is_reconciled: boolean;
  unmatched_statement: { line_no: number; date: string; description: string; amount_minor: number }[];
  unmatched_book: GLCandidate[];
}

export interface BankStatement {
  id: string;
  account_code: string;
  statement_date: string;
  opening_balance_minor: number;
  closing_balance_minor: number;
  reference: string;
  status: BankStatementStatus;
  lines: BankStatementLine[];
  reconciliation?: ReconciliationSummary;
}

export function listBankStatements(): Promise<BankStatement[]> {
  return apiFetch<BankStatement[]>("/accounting/bank-statements");
}

export function getBankStatement(id: string): Promise<BankStatement> {
  return apiFetch<BankStatement>(`/accounting/bank-statements/${id}`);
}

export function createBankStatement(payload: {
  account_code: string;
  statement_date: string;
  opening_balance_minor?: number;
  closing_balance_minor: number;
  reference?: string;
  lines: { date: string; amount_minor: number; description?: string }[];
}): Promise<BankStatement> {
  return apiFetch<BankStatement>("/accounting/bank-statements", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function autoMatchStatement(id: string): Promise<BankStatement> {
  return apiFetch<BankStatement>(`/accounting/bank-statements/${id}/auto-match`, { method: "POST", body: "{}" });
}

export function postBankAdjustment(id: string, payload: {
  amount_minor: number;
  contra_account_code: string;
  memo?: string;
}): Promise<BankStatement> {
  return apiFetch<BankStatement>(`/accounting/bank-statements/${id}/adjustment`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function reconcileStatement(id: string): Promise<BankStatement> {
  return apiFetch<BankStatement>(`/accounting/bank-statements/${id}/reconcile`, { method: "POST", body: "{}" });
}

export function listMatchCandidates(id: string): Promise<GLCandidate[]> {
  return apiFetch<GLCandidate[]>(`/accounting/bank-statements/${id}/candidates`);
}

export function matchBankLine(lineId: string, journalLineId: number): Promise<BankStatement> {
  return apiFetch<BankStatement>(`/accounting/bank-statement-lines/${lineId}/match`, {
    method: "POST",
    body: JSON.stringify({ journal_line_id: journalLineId }),
  });
}

export function unmatchBankLine(lineId: string): Promise<BankStatement> {
  return apiFetch<BankStatement>(`/accounting/bank-statement-lines/${lineId}/match`, { method: "DELETE" });
}

// ---- Fixed assets ----

export type AssetStatus = "active" | "disposed";

export interface FixedAsset {
  id: string;
  code: string;
  name: string;
  category: string;
  acquisition_date: string;
  in_service_date: string;
  cost_minor: number;
  salvage_minor: number;
  useful_life_months: number;
  accumulated_depreciation_minor: number;
  net_book_value_minor: number;
  months_depreciated: number;
  status: AssetStatus;
  acquire_journal_number: string;
  disposed_date: string | null;
  disposal_proceeds_minor: number | null;
  disposal_gain_loss_minor: number | null;
  disposal_journal_number: string;
}

export interface AssetRegisterRow {
  code: string;
  name: string;
  category: string;
  acquisition_date: string;
  cost_minor: number;
  accumulated_depreciation_minor: number;
  net_book_value_minor: number;
  status: AssetStatus;
}

export interface AssetRegisterReport {
  rows: AssetRegisterRow[];
  total_cost: number;
  total_accumulated: number;
  total_nbv: number;
}

export function listAssets(): Promise<FixedAsset[]> {
  return apiFetch<FixedAsset[]>("/accounting/assets");
}

export function getAsset(code: string): Promise<FixedAsset> {
  return apiFetch<FixedAsset>(`/accounting/assets/${encodeURIComponent(code)}`);
}

export function acquireAsset(payload: {
  code: string;
  name: string;
  category?: string;
  acquisition_date: string;
  cost_minor: number;
  salvage_minor?: number;
  useful_life_months: number;
  funding_account_code?: string;
}): Promise<FixedAsset> {
  return apiFetch<FixedAsset>("/accounting/assets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function disposeAsset(
  code: string,
  payload: { disposed_date: string; proceeds_minor: number; proceeds_account_code?: string },
): Promise<FixedAsset> {
  return apiFetch<FixedAsset>(`/accounting/assets/${encodeURIComponent(code)}/dispose`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface DepreciationRunResult {
  period_code: string;
  count: number;
  total_minor: number;
}

export function runDepreciation(period_code: string, date: string): Promise<DepreciationRunResult> {
  return apiFetch<DepreciationRunResult>("/accounting/assets/depreciation-run", {
    method: "POST",
    body: JSON.stringify({ period_code, date }),
  });
}

export function assetRegister(): Promise<AssetRegisterReport> {
  return apiFetch<AssetRegisterReport>("/accounting/reports/asset-register");
}

export function vatReturn(from: string, to: string): Promise<VatReturnReport> {
  const q = new URLSearchParams({ from, to });
  return apiFetch<VatReturnReport>(`/accounting/reports/vat-return?${q.toString()}`);
}
