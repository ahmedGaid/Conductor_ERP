import { useTranslation } from "react-i18next";

import { directionFor } from "../i18n";
import { Bdi } from "../components/Bdi";
import "./DashboardPage.css";

export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "ar";
  const dir = directionFor(lang);

  return (
    <section className="dashboard">
      <h1>{t("dashboard.heading")}</h1>
      <div className="dashboard__card">
        <h2>{t("dashboard.welcome")}</h2>
        <p>{t("dashboard.intro")}</p>
        <p className="dashboard__meta">
          {t("dashboard.directionNote", { dir, lang })} <Bdi>[{lang} / {dir}]</Bdi>
        </p>
      </div>
    </section>
  );
}
