import { useTranslation } from "react-i18next";

import { AskView } from "../../assistant/AskView";
import { NavIcon } from "../../app/icons";
import "./assistant.css";

export function AssistantPage() {
  const { t } = useTranslation();

  return (
    <section className="assistant-page">
      <header className="assistant-head">
        <span className="assistant-head__icon" aria-hidden="true">
          <NavIcon name="sparkle" />
        </span>
        <div>
          <h1 className="assistant-head__title">{t("assistant.title")}</h1>
          <p className="assistant-head__subtitle">{t("assistant.subtitle")}</p>
        </div>
      </header>

      <AskView />
    </section>
  );
}
