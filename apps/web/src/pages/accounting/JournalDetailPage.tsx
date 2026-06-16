import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { getJournal, type JournalEntry } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function JournalDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error } = useAsync<JournalEntry>(() => getJournal(id as string), [id]);

  return (
    <section className="acct-page">
      <h1>{t("nav.accounting")}</h1>
      <AccountingNav />

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

      {data && (
        <div className="card acct-page">
          <div className="acct-page__head">
            <h2 className="latin">{data.number}</h2>
            <span className="latin muted">
              {data.date} · {data.period_code} · {data.status}
            </span>
          </div>
          {data.memo && <p className="muted">{data.memo}</p>}

          <div className="acct-table-wrap">
            <table className="acct-table">
              <thead>
                <tr>
                  <th>{t("accounting.entry.account")}</th>
                  <th className="acct-table__num">{t("accounting.entry.debit")}</th>
                  <th className="acct-table__num">{t("accounting.entry.credit")}</th>
                  <th>{t("accounting.entry.lineMemo")}</th>
                </tr>
              </thead>
              <tbody>
                {data.lines.map((l) => (
                  <tr key={l.line_no}>
                    <td>
                      <Bdi>{l.account_code}</Bdi> · {l.account_name}
                    </td>
                    <td className="acct-table__num">
                      <Bdi>{l.debit ? formatMinor(l.debit, data.currency) : ""}</Bdi>
                    </td>
                    <td className="acct-table__num">
                      <Bdi>{l.credit ? formatMinor(l.credit, data.currency) : ""}</Bdi>
                    </td>
                    <td>{l.memo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
