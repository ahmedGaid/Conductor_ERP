import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";

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
import { getConfidence, type ConfidenceSignal } from "../api/confidence";
import { currentPeriod, pctChange, previousPeriod } from "../lib/dates";
import { formatMinor } from "../lib/money";
import { useAsync } from "../hooks/useAsync";
import { ErrorState } from "../components/ErrorState";
import { GettingStarted } from "./GettingStarted";
import { MilestoneBanner } from "./MilestoneBanner";
import { NavIcon } from "../app/icons";
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
  confidence: ConfidenceSignal[];
}

async function loadDashboard(): Promise<DashboardData> {
  const [me, current, previous, cash, journals, orders, pos, tickets, failedNotifs, confidence] =
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
      getConfidence().then((r) => r.signals).catch(() => [] as ConfidenceSignal[]),
    ]);
  return { username: me.username, current, previous, cash, journals, orders, pos, tickets, failedNotifs, confidence };
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
  const secondaryWidgets = widgets.filter((w) => w !== "attention" && w !== "confidence");

  // "More insight" (expenses/cash flow/journals/shortcuts) stays closed by default so the first
  // glance is short: numbers, what needs you, confidence, done.
  const [moreExpanded, setMoreExpanded] = useState(false);

  return (
    <section className="dash">
      <div className="page-head">
        <div>
          <h1 className="page-title">
            {data
              ? t(`dashboard.greeting.${greetingKey()}`, { name: data.username })
              : t("dashboard.heading")}
          </h1>
          <p className="page-subtitle">{t("dashboard.subtitle")}</p>
        </div>
        <span className="dash__period">{currentPeriod()}</span>
      </div>

      <GettingStarted />
      <MilestoneBanner />

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <KpiStrip
            items={[
              {
                key: "revenue",
                label: t("dashboard.totalRevenue"),
                value: formatMinor(data.current.total_revenue),
                delta: pctChange(data.current.total_revenue, data.previous.total_revenue),
              },
              {
                key: "expenses",
                label: t("dashboard.totalExpenses"),
                value: formatMinor(data.current.total_expenses),
                delta: pctChange(data.current.total_expenses, data.previous.total_expenses),
                invertDelta: true,
              },
              {
                key: "profit",
                label: t("dashboard.netProfit"),
                value: formatMinor(data.current.net_income),
                delta: pctChange(data.current.net_income, data.previous.net_income),
              },
              {
                key: "cash",
                label: t("dashboard.cashBalance"),
                value: formatMinor(data.cash.closing_balance),
                hint: t("dashboard.asOfNow"),
                negative: data.cash.closing_balance < 0,
                hintTo: data.cash.closing_balance < 0 ? "/accounting/cash-flow" : undefined,
              },
            ]}
          />

          {widgets.includes("attention") && <AttentionPanel data={data} />}
          {widgets.includes("confidence") && <ConfidencePanel signals={data.confidence} />}

          {secondaryWidgets.length > 0 && (
            <div className="dash__more">
              <div className="dash__panel-head">
                <h2>{t("dashboard.moreInsight.title")}</h2>
                <button
                  type="button"
                  className="dash__more-toggle"
                  aria-expanded={moreExpanded}
                  onClick={() => setMoreExpanded((v) => !v)}
                >
                  {moreExpanded ? t("dashboard.moreInsight.hide") : t("dashboard.moreInsight.show")}
                </button>
              </div>
              {moreExpanded && (
                <div className="dash__row">
                  {secondaryWidgets.map((w) => {
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
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}

interface KpiItem {
  key: string;
  label: string;
  value: string;
  delta?: number | null;
  invertDelta?: boolean;
  negative?: boolean;
  hint?: string;
  /** When set (with `negative`), the hint links to the full report instead of being plain text. */
  hintTo?: string;
}

// The four headline numbers as one text-forward strip, not four bordered cards — the numbers
// carry the weight, no shell needed around them.
function KpiStrip({ items }: { items: KpiItem[] }) {
  const { t } = useTranslation();
  return (
    <div className="dash__kpi-strip">
      {items.map((it) => {
        const hasDelta = it.delta !== undefined && it.delta !== null;
        const good = hasDelta ? (it.invertDelta ? (it.delta as number) < 0 : (it.delta as number) >= 0) : false;
        const trendWord = hasDelta ? t(good ? "dashboard.deltaUp" : "dashboard.deltaDown") : undefined;
        const hintText = it.negative ? t("dashboard.cashNegative") : (it.hint ?? t("dashboard.vsLastMonth"));
        const ariaLabel = [
          it.label,
          it.value,
          hasDelta ? `${Math.abs(it.delta as number)}% ${trendWord}` : null,
          hintText,
        ]
          .filter(Boolean)
          .join(", ");

        return (
          <div
            key={it.key}
            className={it.negative ? "dash__kpi dash__kpi--negative" : "dash__kpi"}
            role="group"
            aria-label={ariaLabel}
          >
            <span className="dash__kpi-label" aria-hidden="true">{it.label}</span>
            <span className="dash__kpi-value" aria-hidden="true"><Bdi>{it.value}</Bdi></span>
            <span className="dash__kpi-foot">
              {hasDelta ? (
                <span
                  className={good ? "dash__kpi-delta dash__kpi-delta--up" : "dash__kpi-delta dash__kpi-delta--down"}
                  aria-hidden="true"
                >
                  <NavIcon name={good ? "trendUp" : "trendDown"} />
                  <Bdi>{Math.abs(it.delta as number)}%</Bdi>
                </span>
              ) : null}
              {it.negative && it.hintTo ? (
                <Link to={it.hintTo} className="dash__kpi-hint dash__kpi-hint--negative dash__kpi-hint--link">
                  {hintText}
                </Link>
              ) : (
                <span
                  className={it.negative ? "dash__kpi-hint dash__kpi-hint--negative" : "dash__kpi-hint"}
                  aria-hidden="true"
                >
                  {hintText}
                </span>
              )}
            </span>
          </div>
        );
      })}
    </div>
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
    items.push({ key: "salesApprovals", icon: "flag", to: "/sales",
      text: t("dashboard.attention.salesApprovals", { count: salesApprovals }) });
  if (poApprovals)
    items.push({ key: "poApprovals", icon: "flag", to: "/purchasing",
      text: t("dashboard.attention.poApprovals", { count: poApprovals }) });
  if (receivable.length)
    items.push({ key: "receivables", icon: "trendUp", to: "/sales",
      text: t("dashboard.attention.receivables", { amount: formatMinor(recvAmount), count: receivable.length }) });
  if (payable.length)
    items.push({ key: "payables", icon: "trendDown", to: "/purchasing",
      text: t("dashboard.attention.payables", { amount: formatMinor(payAmount), count: payable.length }) });
  if (breachedTickets)
    items.push({ key: "breachedTickets", icon: "clock", to: "/crm/tickets", tone: "danger",
      text: t("dashboard.attention.breachedTickets", { count: breachedTickets }) });
  if (failedMessages)
    items.push({ key: "failedMessages", icon: "close", to: "/notifications", tone: "warn",
      text: t("dashboard.attention.failedMessages", { count: failedMessages }) });

  return (
    <div className={`card dash__panel dash__attn${items.length ? " dash__attn--active" : ""}`}>
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
                <span className="dash__attn-icon" aria-hidden="true"><NavIcon name={it.icon} /></span>
                <span className="dash__attn-text">{it.text}</span>
                <span className="dash__attn-arrow" aria-hidden="true"><NavIcon name="chevronRight" /></span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const CONFIDENCE_META: Record<ConfidenceSignal["key"], { icon: string; to: string }> = {
  books: { icon: "accounting", to: "/accounting/trial-balance" },
  vat: { icon: "einvoice", to: "/accounting/vat-return" },
  backups: { icon: "archive", to: "/settings" },
  stock: { icon: "inventory", to: "/inventory" },
  assistant: { icon: "sparkle", to: "/assistant" },
};

// System Confidence panel — the reassurance complement to "Needs attention today": a calm,
// positive strip. Every signal shows regardless of state (ok or warn) so it reads as a true
// checklist, not a filtered highlight reel; colour always pairs with the word ok/warn, never
// colour alone (monochrome-chrome rule).
function ConfidencePanel({ signals }: { signals: ConfidenceSignal[] }) {
  const { t } = useTranslation();
  const allOk = signals.every((s) => s.status === "ok");
  // Collapsed to a one-line summary when everything's fine — the full checklist (every signal,
  // regardless of state) is still one click away, never removed, just not the default weight on a
  // screen that's already 6-8 panels deep. Auto-expands whenever anything needs a look.
  const [expanded, setExpanded] = useState(!allOk);
  if (signals.length === 0) return null;

  return (
    <div className="card dash__panel dash__confidence">
      <div className="dash__panel-head">
        <h2>{t("dashboard.confidence.title")}</h2>
        {allOk && (
          <button
            type="button"
            className="dash__confidence-toggle"
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? t("dashboard.confidence.hideDetails") : t("dashboard.confidence.showDetails")}
          </button>
        )}
      </div>
      {allOk && !expanded ? (
        <p className="dash__confidence-summary">
          <span className="dash__confidence-summary-icon" aria-hidden="true">
            <NavIcon name="checkCircle" />
          </span>
          {t("dashboard.confidence.allOk")}
        </p>
      ) : (
        <ul className="dash__confidence-list">
          {signals.map((s) => {
            const meta = CONFIDENCE_META[s.key];
            return (
              <li key={s.key}>
                <Link
                  className={`dash__confidence-item dash__confidence-item--${s.status}`}
                  to={meta.to}
                >
                  <span className="dash__confidence-icon" aria-hidden="true">
                    <NavIcon name={s.status === "ok" ? "checkCircle" : meta.icon} />
                  </span>
                  <span className="dash__confidence-text">
                    {t(`dashboard.confidence.${s.key}.${s.status}`)}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function TopExpenses({ report }: { report: IncomeStatementReport }) {
  const { t } = useTranslation();
  const top = useMemo(() =>
    [...report.expenses].sort((a, b) => b.amount - a.amount).slice(0, 5),
    [report.expenses]
  );
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
              <span className="dash__shortcut-icon" aria-hidden="true"><NavIcon name="plus" /></span>
              <span>{t(`dashboard.action.${s.key}`)}</span>
              <span className="dash__shortcut-arrow" aria-hidden="true"><NavIcon name="chevronRight" /></span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
