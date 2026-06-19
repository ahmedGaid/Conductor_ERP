import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { listJournals } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { EmptyState } from "../../components/EmptyState";
import { AccountingNav } from "./AccountingNav";
import "./accounting.css";

export function JournalListPage() {
  const { t } = useTranslation();
  const { data, loading, error } = useAsync(() => listJournals(), [], "accounting:journals");

  return (
    <section className="acct-page">
      <AccountingNav />
      <div className="acct-page__head">
        <Link className="btn btn--primary" to="/accounting/journals/new">
          {t("accounting.tabs.newEntry")}
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
          title={t("accounting.journals.empty")}
          hint={t("common.emptyHint")}
          action={{ label: t("accounting.tabs.newEntry"), to: "/accounting/journals/new" }}
        />
      )}

      {data && data.length > 0 && (
        <div className="card acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t("accounting.journals.number")}</th>
                <th>{t("accounting.entry.date")}</th>
                <th>{t("accounting.journals.period")}</th>
                <th>{t("accounting.entry.memo")}</th>
                <th className="acct-table__num">{t("accounting.journals.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.map((e) => {
                const total = e.lines.reduce((s, l) => s + l.debit, 0);
                return (
                  <tr key={e.id}>
                    <td>
                      <Link to={`/accounting/journals/${e.id}`} className="latin">
                        {e.number}
                      </Link>
                    </td>
                    <td className="latin">{e.date}</td>
                    <td className="latin">{e.period_code}</td>
                    <td>{e.memo}</td>
                    <td className="acct-table__num">
                      <Bdi>{formatMinor(total, e.currency)}</Bdi>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
