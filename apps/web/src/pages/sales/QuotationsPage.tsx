import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listQuotations } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { SalesNav } from "./SalesNav";
import "./sales.css";

export function QuotationsPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(() => listQuotations(), [], "sales:quotations");

  return (
    <section className="sales-page">
      <SalesNav />
      <div className="sales-page__head">
        <Link className="btn btn--primary" to="/sales/quotations/new">
          {t("sales.tabs.newQuotation")}
        </Link>
      </div>

      {loading && (
        <div className="page-skeleton" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      )}
      {error && <p className="error-text">{error}</p>}
      {data && data.length === 0 && (
        <EmptyState
          title={t("sales.quotations.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("sales.tabs.newQuotation"), to: "/sales/quotations/new" }}
        />
      )}

      {data && data.length > 0 && (
        <div className="card sales-table-wrap">
          <table className="sales-table">
            <thead>
              <tr>
                <th>{t("sales.quotations.number")}</th>
                <th>{t("sales.orders.customer")}</th>
                <th>{t("accounting.entry.date")}</th>
                <th>{t("accounting.account.type")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((q) => (
                <tr key={q.id}>
                  <td>
                    <Link to={`/sales/quotations/${q.id}`} className="latin">{q.number}</Link>
                  </td>
                  <td>{q.customer_name}</td>
                  <td className="latin muted">{q.quote_date}</td>
                  <td>
                    <span className={`sales-badge sales-badge--${q.status}`}>
                      {t(`sales.quotationStatus.${q.status}`)}
                    </span>
                  </td>
                  <td className="sales-table__num"><Bdi>{formatMinor(q.subtotal_minor, q.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
