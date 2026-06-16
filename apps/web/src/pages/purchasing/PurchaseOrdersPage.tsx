import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listPurchaseOrders } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

export function PurchaseOrdersPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(() => listPurchaseOrders(), [], "purchasing:orders");

  return (
    <section className="pur-page">
      <div className="pur-page__head">
        <h1>{t("nav.purchasing")}</h1>
        <Link className="btn btn--primary" to="/purchasing/orders/new">
          {t("purchasing.tabs.newOrder")}
        </Link>
      </div>
      <PurchasingNav />

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
      {data && data.length === 0 && <p className="muted">{t("purchasing.orders.empty")}</p>}

      {data && data.length > 0 && (
        <div className="card pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <th>{t("purchasing.orders.number")}</th>
                <th>{t("purchasing.orders.supplier")}</th>
                <th>{t("accounting.entry.date")}</th>
                <th>{t("accounting.account.type")}</th>
                <th className="pur-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((o) => (
                <tr key={o.id}>
                  <td>
                    <Link to={`/purchasing/orders/${o.id}`} className="latin">{o.number}</Link>
                  </td>
                  <td>{o.supplier_name}</td>
                  <td className="latin muted">{o.order_date}</td>
                  <td>
                    <span className={`pur-badge pur-badge--${o.status}`}>
                      {t(`purchasing.status.${o.status}`)}
                    </span>
                  </td>
                  <td className="pur-table__num"><Bdi>{formatMinor(o.subtotal_minor, o.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
