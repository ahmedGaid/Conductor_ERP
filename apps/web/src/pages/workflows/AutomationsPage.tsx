import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { NavIcon } from "../../app/icons";
import { listTemplates, type WorkflowTemplate } from "../../api/workflowTemplates";
import "./AutomationsPage.css";

const TEMPLATE_ICON: Record<string, string> = {
  approval_above_amount: "checkCircle",
  low_stock_alert: "warning",
  overdue_invoice_reminder: "clock",
  new_lead_followup: "sparkle",
  ticket_escalation: "trendUp",
};

// Template names are already commands ("Ask for approval above an amount"); this key adds the
// one-line outcome so a user can tell what a template does before clicking into it.
const TEMPLATE_DESCRIPTION_KEY: Record<string, string> = {
  approval_above_amount: "automations.templateDescription.approval_above_amount",
  low_stock_alert: "automations.templateDescription.low_stock_alert",
  overdue_invoice_reminder: "automations.templateDescription.overdue_invoice_reminder",
  new_lead_followup: "automations.templateDescription.new_lead_followup",
  ticket_escalation: "automations.templateDescription.ticket_escalation",
};

export function AutomationsPage() {
  const { t, i18n } = useTranslation();
  const { data, loading, error, reload } = useAsync<WorkflowTemplate[]>(() => listTemplates(), []);
  const lang = i18n.language as "ar" | "en";

  return (
    <section className="automations">
      <h1>{t("automations.title")}</h1>
      <p className="muted">{t("automations.subtitle")}</p>

      {loading && <ListSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <h2>{t("automations.templatesHeading")}</h2>
          <div className="automations__grid">
            {data.map((tpl) => (
              <Link key={tpl.id} to={`/workflows/templates/${tpl.id}`} className="card automations__card">
                <span className="automations__card-icon">
                  <NavIcon name={TEMPLATE_ICON[tpl.id] ?? "workflows"} />
                </span>
                <span className="automations__card-text">
                  <span className="automations__card-name">{tpl.name[lang] ?? tpl.name.en}</span>
                  {TEMPLATE_DESCRIPTION_KEY[tpl.id] && (
                    <span className="automations__card-desc">{t(TEMPLATE_DESCRIPTION_KEY[tpl.id])}</span>
                  )}
                </span>
              </Link>
            ))}
          </div>
        </>
      )}

      <div className="automations__footer">
        <Link to="/workflows/build" className="automations__footer-link">
          <NavIcon name="plus" />
          {t("automations.startFromScratch")}
        </Link>
        <Link to="/workflows/advanced" className="automations__footer-link automations__footer-link--muted">
          {t("automations.advanced")}
        </Link>
      </div>
    </section>
  );
}
