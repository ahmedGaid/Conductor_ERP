import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { getJournal, postDraftJournalEntry, type JournalEntry } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { useRecentEntity } from "../../hooks/useRecentEntity";
import { useToast } from "../../app/ToastContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { DocumentPrimaryButton, type DocumentPrimary } from "../../components/DocumentHeader";
import { runOptimistic } from "../../lib/optimistic";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { ErrorState } from "../../components/ErrorState";
import { formatMinor } from "../../lib/money";
import { Bdi } from "../../components/Bdi";
import { PartyLink, type PartyType } from "../../components/PartyLink";
import { EntityLink, type EntityType } from "../../components/EntityLink";
import { Disclosure } from "../../components/Disclosure";
import { ModuleHeader } from "../../components/ModuleHeader";
import { RecordTimeline } from "../../components/RecordTimelineLazy";
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
  const { data, loading, error, reload, mutate } = useAsync<JournalEntry>(() => getJournal(id as string), [id], `accounting:journal:${id}`);
  useRecentEntity(data?.number);
  const toast = useToast();

  useSetDocumentCrumb(data?.number);

  // Post a DRAFT entry to the ledger: flip to "posted" instantly, reconcile with the server's entry,
  // toast the posted number on success (roll back + error toast on failure — e.g. a closed period).
  function act() {
    if (!data) return;
    void runOptimistic<JournalEntry, JournalEntry>({
      current: data,
      mutate,
      optimistic: (e) => ({ ...e, status: "posted" }),
      request: () => postDraftJournalEntry(data.id),
      settle: (_predicted, updated) => updated,
      toast,
      successFrom: (updated) => t("accounting.entry.toastPosted", { number: updated.number }),
    });
  }

  // A draft entry gains the first (and only) lifecycle primary: Post. Once posted the journal is
  // read-only — no primary; the ⋯ menu carries print / export / share in every state.
  function primaryAction(): DocumentPrimary | null {
    if (!data || data.status !== "draft") return null;
    return { label: t("accounting.entry.post"), onClick: act };
  }
  const barPrimary = useMemo(() => {
    const a = primaryAction();
    return a ? <DocumentPrimaryButton action={a} /> : undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, t]);
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (!data) return [];
    return [
      { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(data.number) },
      { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(data.number) },
      {
        key: "share",
        label: t("document.share"),
        icon: "share",
        onClick: () =>
          void copyShareLink(`/accounting/journals/${id}`).then((ok) =>
            toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
          ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, t]);
  useSetPageActions({ primary: barPrimary, menuItems: barMenu });

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

          <Disclosure summary={t("timeline.title")}>
            <RecordTimeline entityType="JournalEntry" entityId={data.number} />
          </Disclosure>
        </div>
      )}
    </section>
  );
}
