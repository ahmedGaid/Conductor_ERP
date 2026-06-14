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
}

export interface JournalLine {
  line_no: number;
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
  memo: string;
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
}

function rangeQuery(params: RangeParams): string {
  const q = new URLSearchParams();
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  if (params.period) q.set("period", params.period);
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
