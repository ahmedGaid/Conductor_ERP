import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  listETAInvoices,
  pollETAInvoice,
  submitETAInvoice,
  type ETAInvoice,
} from "../../api/einvoice";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function EInvoicesPage() {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useAsync(() => listETAInvoices(), []);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(id: string, fn: () => Promise<ETAInvoice>) {
    setBusy(id);
    setActionError(null);
    try {
      await fn();
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="acct-page">
      <h1>{t("nav.accounting")}</h1>
      <AccountingNav />

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}
      {actionError && <p className="error-text">{actionError}</p>}
      {data && data.length === 0 && <p className="muted">{t("accounting.einvoice.empty")}</p>}

      {data && data.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.einvoice.invoice")}</th>
                <th>{t("sales.orders.customer")}</th>
                <th className="acct-table__num">{t("accounting.einvoice.tax")}</th>
                <th className="acct-table__num">{t("accounting.einvoice.total")}</th>
                <th>{t("accounting.einvoice.uuid")}</th>
                <th>{t("accounting.account.type")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((e) => (
                <tr key={e.id}>
                  <td className="latin">{e.invoice_number}</td>
                  <td>{e.customer_name || e.customer_code}</td>
                  <td className="acct-table__num"><Bdi>{formatMinor(e.tax_minor, e.currency)}</Bdi></td>
                  <td className="acct-table__num"><Bdi>{formatMinor(e.total_minor, e.currency)}</Bdi></td>
                  <td className="latin muted">{e.uuid ? `${e.uuid.slice(0, 12)}…` : "—"}</td>
                  <td>
                    <span className={`sales-badge sales-badge--${e.status}`}>
                      {t(`accounting.einvoice.status.${e.status}`)}
                    </span>
                  </td>
                  <td>
                    {e.status === "draft" && (
                      <button className="btn btn--sm" disabled={busy === e.id} onClick={() => run(e.id, () => submitETAInvoice(e.id))}>
                        {t("accounting.einvoice.submit")}
                      </button>
                    )}
                    {e.status === "submitted" && (
                      <button className="btn btn--sm" disabled={busy === e.id} onClick={() => run(e.id, () => pollETAInvoice(e.id))}>
                        {t("accounting.einvoice.poll")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
