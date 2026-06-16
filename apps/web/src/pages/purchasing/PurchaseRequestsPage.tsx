import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listRequests } from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PurchasingNav } from "./PurchasingNav";
import "./purchasing.css";

export function PurchaseRequestsPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(() => listRequests(), []);

  return (
    <section className="pur-page">
      <div className="pur-page__head">
        <h1>{t("nav.purchasing")}</h1>
        <Link className="btn btn--primary" to="/purchasing/requests/new">
          {t("purchasing.tabs.newRequest")}
        </Link>
      </div>
      <PurchasingNav />

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}
      {data && data.length === 0 && <p className="muted">{t("purchasing.requests.empty")}</p>}

      {data && data.length > 0 && (
        <div className="card pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <th>{t("purchasing.requests.number")}</th>
                <th>{t("purchasing.orders.supplier")}</th>
                <th>{t("accounting.entry.date")}</th>
                <th>{t("accounting.account.type")}</th>
                <th className="pur-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/purchasing/requests/${r.id}`} className="latin">{r.number}</Link>
                  </td>
                  <td>{r.supplier_name}</td>
                  <td className="latin muted">{r.request_date}</td>
                  <td>
                    <span className={`pur-badge pur-badge--${r.status}`}>
                      {t(`purchasing.requestStatus.${r.status}`)}
                    </span>
                  </td>
                  <td className="pur-table__num"><Bdi>{formatMinor(r.subtotal_minor, r.currency)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
