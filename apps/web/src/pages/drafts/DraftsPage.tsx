import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { listDrafts, discardDraft, type WorkSessionDraft } from "../../api/workSessions";
import { useAsync } from "../../hooks/useAsync";
import { EmptyState } from "../../components/EmptyState";
import { relativeTime } from "../../lib/relativeTime";
import "./drafts.css";

// Where "Continue" sends the user for each workflow. The create forms re-detect their own draft on
// mount (recovery banner); Smart Import resumes by batch id (its existing resume-by-URL path).
function routeFor(d: WorkSessionDraft): string {
  switch (d.workflow_key) {
    case "sales.customer.create":
      return "/sales/customers";
    case "sales.customer.edit":
      return d.related_entity_id ? `/sales/customers/${d.related_entity_id}` : "/sales/customers";
    case "inventory.item.create":
      return "/inventory/items";
    case "inventory.item.edit":
      return d.related_entity_id ? `/inventory/items/${d.related_entity_id}` : "/inventory/items";
    case "sales.order.create":
      return "/sales/orders/new";
    case "sales.order.edit":
      return d.related_entity_id ? `/sales/orders/${d.related_entity_id}/edit` : "/sales";
    case "purchasing.order.create":
      return "/purchasing/orders/new";
    case "purchasing.order.edit":
      return d.related_entity_id ? `/purchasing/orders/${d.related_entity_id}/edit` : "/purchasing";
    case "imports.smart.create":
      return d.related_entity_id ? `/imports/${d.related_entity_id}` : "/imports/new";
    default:
      return "/";
  }
}

export function DraftsPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { data: drafts, loading, reload } = useAsync(listDrafts, [], "worksessions:drafts");

  const rows = useMemo(() => drafts ?? [], [drafts]);

  async function onDiscard(id: string) {
    await discardDraft(id).catch(() => {});
    reload();
  }

  return (
    <section className="page-enter drafts-page">
      <header className="drafts-page__head">
        <h1 className="drafts-page__title">{t("drafts.page.title")}</h1>
        <p className="drafts-page__lede">{t("drafts.page.lede")}</p>
      </header>

      {!loading && rows.length === 0 ? (
        <EmptyState title={t("drafts.page.empty")} />
      ) : (
        <ul className="drafts-list">
          {rows.map((d) => (
            <li key={d.id} className="drafts-list__row card">
              <div className="drafts-list__text">
                <span className="drafts-list__name">
                  {t(`drafts.workflow.${d.workflow_key}`, { defaultValue: d.entity_type || d.workflow_key })}
                </span>
                <span className="drafts-list__when muted">
                  {t("drafts.page.lastUpdated", { when: relativeTime(d.last_active_at, i18n.language) })}
                </span>
              </div>
              <div className="drafts-list__actions">
                <button type="button" className="btn btn--sm btn--primary" onClick={() => navigate(routeFor(d))}>
                  {t("drafts.page.continue")}
                </button>
                <button type="button" className="btn btn--sm btn--ghost" onClick={() => onDiscard(d.id)}>
                  {t("drafts.page.discard")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
