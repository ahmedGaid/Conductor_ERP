import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { executeAction, type ActionProposal, type ActionRecord } from "../api/assistant";
import { NavIcon } from "../app/icons";
import { Bdi } from "../components/Bdi";
import { EntityLink } from "../components/EntityLink";

// Each proposable action's home-module icon (for record chips) and its human title key.
const ACTION_ICON: Record<string, string> = {
  create_sales_order_draft: "sales",
  create_purchase_request_draft: "purchasing",
  create_customer: "crm",
  create_quotation_draft: "sales",
  convert_quotation: "sales",
  edit_sales_order_draft: "sales",
  create_purchase_order_draft: "purchasing",
  convert_purchase_request: "purchasing",
  create_supplier: "purchasing",
};

// A record the action touches (proposal) or created (result), rendered as a click-through. Customer/
// supplier/item resolve through EntityLink by their code; the UUID-keyed documents link straight.
function RecordLink({ r, onNavigate }: { r: ActionRecord; onNavigate?: () => void }) {
  if (r.type === "order") {
    return (
      <Link className="assistant-cite" to={`/sales/orders/${r.value}`} onClick={onNavigate}>
        <NavIcon name="sales" />
        <Bdi>{r.label}</Bdi>
      </Link>
    );
  }
  if (r.type === "purchaseRequest") {
    return (
      <Link className="assistant-cite" to={`/purchasing/requests/${r.value}`} onClick={onNavigate}>
        <NavIcon name="purchasing" />
        <Bdi>{r.label}</Bdi>
      </Link>
    );
  }
  if (r.type === "purchaseOrder") {
    return (
      <Link className="assistant-cite" to={`/purchasing/orders/${r.value}`} onClick={onNavigate}>
        <NavIcon name="purchasing" />
        <Bdi>{r.label}</Bdi>
      </Link>
    );
  }
  if (r.type === "quotation") {
    return (
      <Link className="assistant-cite" to={`/sales/quotations/${r.value}`} onClick={onNavigate}>
        <NavIcon name="sales" />
        <Bdi>{r.label}</Bdi>
      </Link>
    );
  }
  const icon = r.type === "supplier" ? "purchasing" : r.type === "item" ? "inventory" : "crm";
  return (
    <EntityLink className="assistant-cite" type={r.type} value={r.value} onClick={onNavigate}>
      <NavIcon name={icon} />
      <Bdi>{r.label}</Bdi>
    </EntityLink>
  );
}

interface ActionCardProps {
  messageId: number;
  proposal: ActionProposal;
  // Persist the settled proposal back onto its message so a reload shows the same state.
  onResolved: (messageId: number, proposal: ActionProposal) => void;
  onNavigate?: () => void;
}

/**
 * A write the agent prepared: summary + real record links + risks, with Confirm / Dismiss. Nothing
 * is created until Confirm runs the module contract; the card then flips to its result state (created
 * document link). Consumed/dismissed cards stay visibly settled and are reload-safe — the state lives
 * in the message meta, updated through `onResolved`.
 */
export function ActionCard({ messageId, proposal, onResolved, onNavigate }: ActionCardProps) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState<"confirm" | "dismiss" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const title = t(`assistant.action.titles.${proposal.action}`);
  const icon = ACTION_ICON[proposal.action] ?? "sparkle";

  async function resolve(decision: "confirm" | "dismiss") {
    if (busy) return;
    setBusy(decision);
    setError(null);
    try {
      const res = await executeAction(messageId, decision);
      onResolved(messageId, {
        ...proposal,
        status: res.status,
        ...(res.status === "confirmed" && res.summary
          ? { result: { summary: res.summary, links: res.links ?? [] } }
          : {}),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("assistant.errorLine"));
    } finally {
      setBusy(null);
    }
  }

  // --- result state (confirmed) ----------------------------------------------------------------
  if (proposal.status === "confirmed") {
    const result = proposal.result;
    return (
      <div className="action-card action-card--done">
        <p className="action-card__result" dir="auto">
          <NavIcon name="checkCircle" />
          {result?.summary ?? t("assistant.action.executed")}
        </p>
        {result?.links?.length ? (
          <ul className="assistant-cites">
            {result.links.map((r) => (
              <li key={`${r.type}:${r.value}`}>
                <RecordLink r={r} onNavigate={onNavigate} />
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  }

  // --- dismissed state -------------------------------------------------------------------------
  if (proposal.status === "dismissed") {
    return (
      <div className="action-card action-card--dismissed">
        <p className="action-card__settled">
          <NavIcon name="close" />
          {t("assistant.action.dismissed")}
        </p>
      </div>
    );
  }

  // --- pending state ---------------------------------------------------------------------------
  return (
    <div className="action-card">
      <header className="action-card__head">
        <span className="action-card__icon" aria-hidden="true">
          <NavIcon name={icon} />
        </span>
        <span className="action-card__title">{title}</span>
        {proposal.affected > 0 && (
          <span className="action-card__count">
            {t("assistant.action.affected", { count: proposal.affected })}
          </span>
        )}
      </header>

      <ul className="action-card__summary">
        {proposal.summary.map((line, i) => (
          <li key={i} dir="auto">{line}</li>
        ))}
      </ul>

      {proposal.records.length > 0 && (
        <ul className="assistant-cites action-card__records">
          {proposal.records.map((r) => (
            <li key={`${r.type}:${r.value}`}>
              <RecordLink r={r} onNavigate={onNavigate} />
            </li>
          ))}
        </ul>
      )}

      {proposal.risks.length > 0 && (
        <div className="action-card__risks">
          <span className="action-card__risks-label">{t("assistant.action.risks")}</span>
          <ul>
            {proposal.risks.map((risk, i) => (
              <li key={i} dir="auto">
                <NavIcon name="flag" />
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="action-card__error" dir="auto">{error}</p>}

      <footer className="action-card__foot">
        <button
          type="button"
          className="action-card__confirm"
          onClick={() => void resolve("confirm")}
          disabled={busy !== null}
        >
          {busy === "confirm" ? t("common.loading") : t("assistant.action.confirm")}
        </button>
        <button
          type="button"
          className="action-card__dismiss"
          onClick={() => void resolve("dismiss")}
          disabled={busy !== null}
        >
          {t("assistant.action.dismiss")}
        </button>
      </footer>
    </div>
  );
}
