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
import { ExportButtons } from "../../components/ExportButtons";
import { EInvoiceNav } from "./EInvoiceNav";
import "./einvoice.css";

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
    <section className="ein-page">
      <h1>{t("nav.einvoice")}</h1>
      <EInvoiceNav />

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="error-text">{error}</p>}
      {actionError && <p className="error-text">{actionError}</p>}
      {data && data.length === 0 && <p className="muted">{t("einvoice.empty")}</p>}

      {data && data.length > 0 && <ExportButtons path="/einvoice/invoices" />}

      {data && data.length > 0 && (
        <div className="card ein-table-wrap">
          <table className="ein-table">
            <thead>
              <tr>
                <th>{t("einvoice.invoice")}</th>
                <th>{t("einvoice.customer")}</th>
                <th className="ein-table__num">{t("einvoice.tax")}</th>
                <th className="ein-table__num">{t("einvoice.total")}</th>
                <th>{t("einvoice.uuid")}</th>
                <th>{t("einvoice.statusHeader")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((e) => (
                <tr key={e.id}>
                  <td className="latin">{e.invoice_number}</td>
                  <td>{e.customer_name || e.customer_code}</td>
                  <td className="ein-table__num"><Bdi>{formatMinor(e.tax_minor, e.currency)}</Bdi></td>
                  <td className="ein-table__num"><Bdi>{formatMinor(e.total_minor, e.currency)}</Bdi></td>
                  <td className="latin muted">{e.uuid ? `${e.uuid.slice(0, 12)}…` : "—"}</td>
                  <td>
                    <span className={`ein-badge ein-badge--${e.status}`}>
                      {t(`einvoice.status.${e.status}`)}
                    </span>
                  </td>
                  <td>
                    {e.status === "draft" && (
                      <button className="btn btn--sm" disabled={busy === e.id} onClick={() => run(e.id, () => submitETAInvoice(e.id))}>
                        {t("einvoice.submit")}
                      </button>
                    )}
                    {e.status === "submitted" && (
                      <button className="btn btn--sm" disabled={busy === e.id} onClick={() => run(e.id, () => pollETAInvoice(e.id))}>
                        {t("einvoice.poll")}
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
