import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { getJournal, type JournalEntry } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PartyLink, type PartyType } from "../../components/PartyLink";
import { EntityLink, type EntityType } from "../../components/EntityLink";
import { ModuleHeader } from "../../components/ModuleHeader";
import { AccountingNav } from "./AccountingNav";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./accounting.css";

// A journal's source module tells us which document its reference points to (so the GL can drill
// back to the order that posted it). Other sources (manual, etc.) leave the reference as plain text.
const SOURCE_ENTITY: Record<string, EntityType> = {
  sales: "salesOrder",
  purchasing: "purchaseOrder",
};

export function JournalDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync<JournalEntry>(() => getJournal(id as string), [id], `accounting:journal:${id}`);

  return (
    <section className="acct-page">
      <AccountingNav />

      {loading && (
        <ListSkeleton />
      )}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <div className="card acct-page">
          <ModuleHeader
            title={data.number}
            subtitle={<span className="latin">{data.date} · {data.period_code} · {data.status}</span>}
          />
          {data.memo && (
            <p className="muted">
              {data.party_code ? (
                <PartyLink type={data.party_type as PartyType} code={data.party_code}>
                  {data.memo}
                </PartyLink>
              ) : (
                data.memo
              )}
            </p>
          )}
          {data.reference && SOURCE_ENTITY[data.source] && (
            <p className="muted">
              {t("accounting.entry.sourceDoc")}:{" "}
              <EntityLink type={SOURCE_ENTITY[data.source]} value={data.reference} />
            </p>
          )}

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
