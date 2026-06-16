import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listOrders } from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { SalesNav } from "./SalesNav";
import "./sales.css";

export function OrdersPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(() => listOrders(), [], "sales:orders");

  return (
    <section className="sales-page">
      <div className="sales-page__head">
        <h1>{t("nav.sales")}</h1>
        <Link className="btn btn--primary" to="/sales/orders/new">
          {t("sales.tabs.newOrder")}
        </Link>
      </div>
      <SalesNav />

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
          title={t("sales.orders.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("sales.tabs.newOrder"), to: "/sales/orders/new" }}
        />
      )}

      {data && data.length > 0 && (
        <div className="card sales-table-wrap">
          <table className="sales-table">
            <thead>
              <tr>
                <th>{t("sales.orders.number")}</th>
                <th>{t("sales.orders.customer")}</th>
                <th>{t("accounting.entry.date")}</th>
                <th>{t("accounting.account.type")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link to={`/sales/orders/${o.id}`} className="latin">{o.number}</Link>
                  </td>
                  <td>{o.customer_name}</td>
                  <td className="latin muted">{o.order_date}</td>
                  <td>
                    <span className={`sales-badge sales-badge--${o.status}`}>
                      {t(`sales.status.${o.status}`)}
                    </span>
                  </td>
                  <td className="sales-table__num"><Bdi>{formatMinor(o.subtotal_minor, o.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
