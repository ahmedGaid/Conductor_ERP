import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { listTemplates, type WorkflowTemplate } from "../../api/workflowTemplates";
import "./AutomationsPage.css";

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
                {tpl.name[lang] ?? tpl.name.en}
              </Link>
            ))}
          </div>
        </>
      )}

      <div className="automations__footer">
        <Link to="/workflows/build">{t("automations.startFromScratch")}</Link>
        <Link to="/workflows/advanced">{t("automations.advanced")}</Link>
      </div>
    </section>
  );
}
