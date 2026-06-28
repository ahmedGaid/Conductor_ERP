import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { GeneralLedgerReport } from "../api/accounting";
import { formatMinor } from "../lib/money";
import { Bdi } from "./Bdi";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { ListSkeleton } from "./ListSkeleton";
import "./partyDetail.css";

export interface PartySummaryItem {
  label: string;
  value: string;
}

export interface PartyOrderRow {
  id: string;
  number: string;
  date: string;
  statusLabel: string;
  total: string;
  outstanding: string;
  href: string;
}

interface PartyDetailViewProps {
  nav: ReactNode;
  backHref: string;
  backLabel: string;
  /** Header: party code + name + a "Customer"/"Supplier" caption. */
  code: string;
  name: string;
  typeLabel: string;
  summary: PartySummaryItem[];
  ordersTitle: string;
  orders: PartyOrderRow[];
  ordersEmpty: string;
  ledger: GeneralLedgerReport | null;
  ledgerTitle: string;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  /** Shown when the party code doesn't resolve to a known customer/supplier. */
  notFound?: boolean;
}

export function PartyDetailView({
  nav,
  backHref,
  backLabel,
  code,
  name,
  typeLabel,
  summary,
  ordersTitle,
  orders,
  ordersEmpty,
  ledger,
  ledgerTitle,
  loading,
  error,
  onRetry,
  notFound,
}: PartyDetailViewProps) {
  const { t } = useTranslation();

  return (
    <section className="sales-page">
      {nav}

      <Link className="party-back" to={backHref}>
        ← {backLabel}
      </Link>

      {loading && <ListSkeleton rows={3} />}
      {error && <ErrorState message={error} onRetry={onRetry} />}
      {notFound && !loading && !error && (
        <EmptyState title={t("party.notFound")} hint={t("party.notFoundHint")} />
      )}

      {!loading && !error && !notFound && (
        <>
          <div className="card">
            <header className="party-head">
              <h2>
                <Bdi>{code}</Bdi> — {name}
              </h2>
              <span className="party-head__type">{typeLabel}</span>
            </header>
            <div className="party-summary">
              {summary.map((s) => (
                <div className="party-summary__item" key={s.label}>
                  <span className="party-summary__label">{s.label}</span>
                  <span className="party-summary__value">
                    <Bdi>{s.value}</Bdi>
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="party-section-title">{ordersTitle}</h3>
            {orders.length === 0 ? (
              <EmptyState title={ordersEmpty} />
            ) : (
              <div className="card party-table-wrap">
                <table className="party-table">
                  <thead>
                    <tr>
                      <th>{t("party.col.number")}</th>
                      <th>{t("party.col.date")}</th>
                      <th>{t("party.col.status")}</th>
                      <th className="party-table__num">{t("party.col.total")}</th>
                      <th className="party-table__num">{t("party.col.outstanding")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((o) => (
                      <tr key={o.id}>
                        <td>
                          <Link to={o.href} className="latin">
                            {o.number}
                          </Link>
                        </td>
                        <td className="latin muted">{o.date}</td>
                        <td className="muted">{o.statusLabel}</td>
                        <td className="party-table__num">
                          <Bdi>{o.total}</Bdi>
                        </td>
                        <td className="party-table__num">
                          <Bdi>{o.outstanding}</Bdi>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div>
            <h3 className="party-section-title">{ledgerTitle}</h3>
            <div className="card party-table-wrap">
              <table className="party-table">
                <thead>
                  <tr>
                    <th>{t("accounting.entry.date")}</th>
                    <th>{t("accounting.journals.number")}</th>
                    <th>{t("accounting.entry.memo")}</th>
                    <th className="party-table__num">{t("accounting.entry.debit")}</th>
                    <th className="party-table__num">{t("accounting.entry.credit")}</th>
                    <th className="party-table__num">{t("accounting.report.running")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(ledger?.lines ?? []).map((l, i) => (
                    <tr key={i}>
                      <td className="latin">{l.date}</td>
                      <td className="latin">
                        <Link to={`/accounting/journals/${l.entry_id}`}>{l.entry_number}</Link>
                      </td>
                      <td>
                        {l.memo ? (
                          <Link to={`/accounting/journals/${l.entry_id}`}>{l.memo}</Link>
                        ) : (
                          ""
                        )}
                      </td>
                      <td className="party-table__num">
                        <Bdi>{l.debit ? formatMinor(l.debit) : ""}</Bdi>
                      </td>
                      <td className="party-table__num">
                        <Bdi>{l.credit ? formatMinor(l.credit) : ""}</Bdi>
                      </td>
                      <td className="party-table__num">
                        <Bdi>{formatMinor(l.running_balance)}</Bdi>
                      </td>
                    </tr>
                  ))}
                  {(!ledger || ledger.lines.length === 0) && (
                    <tr>
                      <td colSpan={6} className="muted">
                        {t("accounting.report.noActivity")}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
