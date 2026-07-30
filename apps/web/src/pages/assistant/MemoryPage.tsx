import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  decideMemoryProposal,
  forgetMemory,
  listMemory,
  type MemoryListing,
  type MemoryRow,
  type MemoryScope,
} from "../../api/assistant";
import { NavIcon } from "../../app/icons";
import { useToast } from "../../app/ToastContext";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useAsync } from "../../hooks/useAsync";
import "./memory.css";

interface Pending {
  row: MemoryRow;
  scope: MemoryScope;
}

// Everything the assistant remembers, and the controls to change it (ai-reliability T4.4). This is
// a trust surface: nothing is hidden, every row says where it came from, and deleting really
// deletes (the server hard-deletes the content and keeps only the audit event).
export function MemoryPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const { data, loading, error, reload, mutate } = useAsync(listMemory, [], "assistant:memory");

  const [pending, setPending] = useState<Pending | null>(null);

  const personal = data?.personal ?? [];
  const org = data?.org ?? [];
  const proposal = data?.proposal ?? null;
  const nothingRemembered = personal.length === 0 && org.length === 0;

  function withoutRow(listing: MemoryListing, row: MemoryRow, scope: MemoryScope): MemoryListing {
    return scope === "user"
      ? { ...listing, personal: listing.personal.filter((r) => r.id !== row.id) }
      : { ...listing, org: listing.org.filter((r) => r.id !== row.id) };
  }

  async function confirmForget() {
    const target = pending;
    setPending(null);
    if (!target || !data) return;
    const previous = data;
    mutate(withoutRow(data, target.row, target.scope));
    try {
      await forgetMemory(target.row.id, target.scope);
      toast.show(t("memory.forgotten"), "success");
    } catch {
      mutate(previous);
      toast.show(t("memory.forgetFailed"), "error");
    }
  }

  async function decide(decision: "confirm" | "dismiss") {
    if (!proposal) return;
    try {
      await decideMemoryProposal(decision, proposal.slot, proposal.value);
      toast.show(decision === "confirm" ? t("memory.proposal.saved") : t("memory.proposal.dismissed"),
        "success");
      reload();
    } catch {
      toast.show(t("memory.proposal.failed"), "error");
    }
  }

  function renderRow(row: MemoryRow, scope: MemoryScope) {
    return (
      <li key={`${scope}-${row.id}`} className="memory-row">
        <div className="memory-row__body">
          {row.kind === "slot" ? (
            <p className="memory-row__value">
              <span className="memory-row__slot">{t(`memory.slot.${row.key}`, row.key)}</span>
              <span className="latin">{row.value}</span>
            </p>
          ) : (
            <p className="memory-row__value">{row.value}</p>
          )}
          <p className="memory-row__meta">
            <span className="memory-chip">{t(`memory.source.${row.source}`)}</span>
            <span className="latin muted">{row.created_at.slice(0, 10)}</span>
          </p>
        </div>
        <button
          type="button"
          className="btn btn--sm memory-row__delete"
          aria-label={t("memory.forget")}
          onClick={() => setPending({ row, scope })}
        >
          <NavIcon name="trash" />
        </button>
      </li>
    );
  }

  return (
    <section className="page-enter">
      <header className="module-head">
        <h1 className="module-head__title">{t("memory.title")}</h1>
        <p className="module-head__desc">{t("memory.subtitle")}</p>
      </header>

      {loading && <ListSkeleton rows={3} />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {!loading && !error && proposal && (
        <div className="card memory-proposal">
          <p className="memory-proposal__text">
            {t("memory.proposal.body", {
              setting: t(`memory.slot.${proposal.slot}`, proposal.slot),
              value: proposal.value,
              times: proposal.occurrences,
            })}
          </p>
          <div className="memory-proposal__actions">
            <button type="button" className="btn btn--primary btn--sm" onClick={() => void decide("confirm")}>
              {t("memory.proposal.save")}
            </button>
            <button type="button" className="btn btn--sm" onClick={() => void decide("dismiss")}>
              {t("memory.proposal.dismiss")}
            </button>
          </div>
        </div>
      )}

      {!loading && !error && nothingRemembered && (
        <EmptyState title={t("memory.empty.title")} hint={t("memory.empty.body")} />
      )}

      {!loading && !error && personal.length > 0 && (
        <div className="card memory-section">
          <h2 className="memory-section__title">{t("memory.personal")}</h2>
          <ul className="memory-list">{personal.map((row) => renderRow(row, "user"))}</ul>
        </div>
      )}

      {!loading && !error && org.length > 0 && (
        <div className="card memory-section">
          <h2 className="memory-section__title">{t("memory.organization")}</h2>
          <p className="memory-section__note">{t("memory.organizationNote")}</p>
          <ul className="memory-list">{org.map((row) => renderRow(row, "org"))}</ul>
        </div>
      )}

      <ConfirmDialog
        open={pending != null}
        title={t("memory.forget")}
        body={t("memory.forgetConfirm")}
        confirmLabel={t("memory.forget")}
        danger
        onConfirm={() => void confirmForget()}
        onClose={() => setPending(null)}
      />
    </section>
  );
}
