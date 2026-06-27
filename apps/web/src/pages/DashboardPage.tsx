import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { usePreferences } from "../preferences/PreferencesContext";
import { orderedVisibleWidgets } from "./settings/dashboardWidgets";
import { getMe } from "../api/identity";
import {
  cashFlow,
  incomeStatement,
  listJournals,
  type CashFlowReport,
  type IncomeStatementReport,
  type JournalEntry,
} from "../api/accounting";
import { listOrders, type SalesOrder } from "../api/sales";
import { listPurchaseOrders, type PurchaseOrder } from "../api/purchasing";
import { listTickets, type Ticket } from "../api/crm";
import { listNotifications, type Notification } from "../api/notifications";
import { currentPeriod, pctChange, previousPeriod } from "../lib/dates";
import { formatMinor } from "../lib/money";
import { useAsync } from "../hooks/useAsync";
import { ErrorState } from "../components/ErrorState";
import { GettingStarted } from "./GettingStarted";
import { StatCard } from "../components/StatCard";
import { Bdi } from "../components/Bdi";
import { ListSkeleton } from "../components/ListSkeleton";
import "./DashboardPage.css";

interface DashboardData {
  username: string;
  current: IncomeStatementReport;
  previous: IncomeStatementReport;
  cash: CashFlowReport;
  journals: JournalEntry[];
  // Cross-module signals for the "needs attention" panel. Each is fetched defensively
  // (a role without access — e.g. an accountant on the sales list — simply 403s and that
  // category stays empty) so the dashboard never breaks on a single module being unreachable.
  orders: SalesOrder[];
  pos: PurchaseOrder[];
  tickets: Ticket[];
  failedNotifs: Notification[];
}

async function loadDashboard(): Promise<DashboardData> {
  const [me, current, previous, cash, journals, orders, pos, tickets, failedNotifs] =
    await Promise.all([
      getMe(),
      incomeStatement({ period: currentPeriod() }),
      incomeStatement({ period: previousPeriod() }),
      cashFlow({ period: currentPeriod() }),
      listJournals(),
      listOrders().catch(() => [] as SalesOrder[]),
      listPurchaseOrders().catch(() => [] as PurchaseOrder[]),
      listTickets().catch(() => [] as Ticket[]),
      listNotifications({ status: "failed" }).catch(() => [] as Notification[]),
    ]);
  return { username: me.username, current, previous, cash, journals, orders, pos, tickets, failedNotifs };
}

function greetingKey(): "morning" | "afternoon" | "evening" {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 18) return "afternoon";
  return "evening";
}

const SHORTCUTS = [
  { key: "newJournal", to: "/accounting/journals/new" },
  { key: "newWorkflow", to: "/workflows/new" },
  { key: "chart", to: "/accounting" },
  { key: "trialBalance", to: "/accounting/trial-balance" },
  { key: "incomeStatement", to: "/accounting/income-statement" },
];

export function DashboardPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(loadDashboard, [], "dashboard");
  const { prefs } = usePreferences();
  const widgets = orderedVisibleWidgets(prefs?.dashboard_layout);

  return (
    <section className="dash">
      <div className="page-head">
        <div>
          <h1 className="page-title">
            {data
              ? t(`dashboard.greeting.${greetingKey()}`, { name: data.username })
              : t("dashboard.heading")}{" "}
            <span aria-hidden="true">👋</span>
          </h1>
          <p className="page-subtitle">{t("dashboard.subtitle")}</p>
        </div>
        <span className="dash__period">{currentPeriod()}</span>
      </div>

      <GettingStarted />

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <div className="dash__kpis">
            <StatCard
              label={t("dashboard.totalRevenue")}
              value={formatMinor(data.current.total_revenue)}
              icon="⊕"
              delta={pctChange(data.current.total_revenue, data.previous.total_revenue)}
            />
            <StatCard
              label={t("dashboard.totalExpenses")}
              value={formatMinor(data.current.total_expenses)}
              icon="▤"
              delta={pctChange(data.current.total_expenses, data.previous.total_expenses)}
              invertDelta
            />
            <StatCard
              label={t("dashboard.netProfit")}
              value={formatMinor(data.current.net_income)}
              icon="↗"
              delta={pctChange(data.current.net_income, data.previous.net_income)}
            />
            <StatCard
              label={t("dashboard.cashBalance")}
              value={formatMinor(data.cash.closing_balance)}
              icon="◆"
              hint={t("dashboard.asOfNow")}
            />
          </div>

          {widgets.includes("attention") && <AttentionPanel data={data} />}

          <div className="dash__row">
            {widgets
              .filter((w) => w !== "attention")
              .map((w) => {
                switch (w) {
                  case "expenses":
                    return <TopExpenses key={w} report={data.current} />;
                  case "cashflow":
                    return <CashFlowPanel key={w} report={data.cash} />;
                  case "journals":
                    return <RecentJournals key={w} journals={data.journals} />;
                  case "shortcuts":
                    return <Shortcuts key={w} />;
                  default:
                    return null;
                }
              })}
          </div>
        </>
      )}
    </section>
  );
}

interface AttnItem {
  key: string;
  icon: string;
  text: string;
  to: string;
  tone?: "danger" | "warn";
}

// "Needs attention today" — turns raw module data into the few decisions/risks the user should act
// on now (data → insight → action), rather than another passive number grid. Only non-empty signals
// are shown; when there's nothing, a calm "all clear" line confirms it (a designed empty state).
function AttentionPanel({ data }: { data: DashboardData }) {
  const { t } = useTranslation();

  const salesApprovals = data.orders.filter((o) => o.requires_approval && !o.approved).length;
  const poApprovals = data.pos.filter((p) => p.requires_approval && !p.approved).length;

  const receivable = data.orders.filter((o) => o.outstanding_minor > 0);
  const recvAmount = receivable.reduce((s, o) => s + o.outstanding_minor, 0);
  const payable = data.pos.filter((p) => p.outstanding_minor > 0);
  const payAmount = payable.reduce((s, p) => s + p.outstanding_minor, 0);

  const breachedTickets = data.tickets.filter((tk) => tk.is_breached).length;
  const failedMessages = data.failedNotifs.length;

  const items: AttnItem[] = [];
  if (salesApprovals)
    items.push({ key: "salesApprovals", icon: "⚑", to: "/sales",
      text: t("dashboard.attention.salesApprovals", { count: salesApprovals }) });
  if (poApprovals)
    items.push({ key: "poApprovals", icon: "⚑", to: "/purchasing",
      text: t("dashboard.attention.poApprovals", { count: poApprovals }) });
  if (receivable.length)
    items.push({ key: "receivables", icon: "↘", to: "/sales",
      text: t("dashboard.attention.receivables", { amount: formatMinor(recvAmount), count: receivable.length }) });
  if (payable.length)
    items.push({ key: "payables", icon: "↗", to: "/purchasing",
      text: t("dashboard.attention.payables", { amount: formatMinor(payAmount), count: payable.length }) });
  if (breachedTickets)
    items.push({ key: "breachedTickets", icon: "⏰", to: "/crm/tickets", tone: "danger",
      text: t("dashboard.attention.breachedTickets", { count: breachedTickets }) });
  if (failedMessages)
    items.push({ key: "failedMessages", icon: "✕", to: "/notifications", tone: "warn",
      text: t("dashboard.attention.failedMessages", { count: failedMessages }) });

  return (
    <div className="card dash__panel dash__attn">
      <div className="dash__panel-head">
        <h2>{t("dashboard.attention.title")}</h2>
      </div>
      {items.length === 0 ? (
        <p className="dash__attn-clear">{t("dashboard.attention.allClear")}</p>
      ) : (
        <ul className="dash__attn-list">
          {items.map((it) => (
            <li key={it.key}>
              <Link className={`dash__attn-item${it.tone ? ` dash__attn-item--${it.tone}` : ""}`} to={it.to}>
                <span className="dash__attn-icon" aria-hidden="true">{it.icon}</span>
                <span className="dash__attn-text">{it.text}</span>
                <span className="dash__attn-arrow" aria-hidden="true">›</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TopExpenses({ report }: { report: IncomeStatementReport }) {
  const { t } = useTranslation();
  const top = [...report.expenses].sort((a, b) => b.amount - a.amount).slice(0, 5);
  const total = report.total_expenses || 1;

  return (
    <div className="card dash__panel">
      <div className="dash__panel-head">
        <h2>{t("dashboard.topExpenses")}</h2>
      </div>
      {top.length === 0 && <p className="muted">{t("dashboard.noData")}</p>}
      <ul className="dash__exp-list">
        {top.map((e) => {
          const pct = Math.round((e.amount / total) * 100);
          return (
            <li key={e.account_code} className="dash__exp">
              <div className="dash__exp-row">
                <span>{e.account_name}</span>
                <span className="dash__exp-amount"><Bdi>{formatMinor(e.amount)}</Bdi></span>
              </div>
              <div className="dash__bar">
                <span className="dash__bar-fill" style={{ inlineSize: `${pct}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function CashFlowPanel({ report }: { report: CashFlowReport }) {
  const { t } = useTranslation();
  const max = Math.max(report.cash_in, report.cash_out, 1);
  return (
    <div className="card dash__panel">
      <div className="dash__panel-head">
        <h2>{t("accounting.tabs.cashFlow")}</h2>
      </div>
      <div className="dash__cash-net">
        <span className="muted">{t("dashboard.netCashFlow")}</span>
        <span className="dash__cash-value"><Bdi>{formatMinor(report.net_change)}</Bdi></span>
      </div>
      <div className="dash__cash-bars">
        <CashBar label={t("dashboard.cashIn")} amount={report.cash_in} max={max} tone="in" />
        <CashBar label={t("dashboard.cashOut")} amount={report.cash_out} max={max} tone="out" />
      </div>
      <div className="dash__cash-closing">
        <span className="muted">{t("accounting.report.closing")}</span>
        <span><Bdi>{formatMinor(report.closing_balance)}</Bdi></span>
      </div>
    </div>
  );
}

function CashBar({ label, amount, max, tone }: { label: string; amount: number; max: number; tone: "in" | "out" }) {
  const pct = Math.round((amount / max) * 100);
  return (
    <div className="dash__cashbar">
      <div className="dash__exp-row">
        <span className="muted">{label}</span>
        <span><Bdi>{formatMinor(amount)}</Bdi></span>
      </div>
      <div className="dash__bar">
        <span className={`dash__bar-fill dash__bar-fill--${tone}`} style={{ inlineSize: `${pct}%` }} />
      </div>
    </div>
  );
}

function RecentJournals({ journals }: { journals: JournalEntry[] }) {
  const { t } = useTranslation();
  const recent = journals.slice(0, 6);
  return (
    <div className="card dash__panel">
      <div className="dash__panel-head">
        <h2>{t("dashboard.recentJournals")}</h2>
        <Link className="dash__viewall" to="/accounting/journals">
          {t("dashboard.viewAll")}
        </Link>
      </div>
      {recent.length === 0 && <p className="muted">{t("accounting.journals.empty")}</p>}
      {recent.length > 0 && (
        <table className="dash__table">
          <tbody>
            {recent.map((e) => {
              const total = e.lines.reduce((s, l) => s + l.debit, 0);
              return (
                <tr key={e.id}>
                  <td>
                    <Link to={`/accounting/journals/${e.id}`} className="latin">{e.number}</Link>
                  </td>
                  <td className="muted">{e.memo}</td>
                  <td className="latin muted">{e.date}</td>
                  <td className="dash__table-num"><Bdi>{formatMinor(total, e.currency)}</Bdi></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Shortcuts() {
  const { t } = useTranslation();
  return (
    <div className="card dash__panel">
      <div className="dash__panel-head">
        <h2>{t("dashboard.shortcuts")}</h2>
      </div>
      <ul className="dash__shortcuts">
        {SHORTCUTS.map((s) => (
          <li key={s.key}>
            <Link className="dash__shortcut" to={s.to}>
              <span className="dash__shortcut-icon" aria-hidden="true">+</span>
              <span>{t(`dashboard.action.${s.key}`)}</span>
              <span className="dash__shortcut-arrow" aria-hidden="true">›</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
