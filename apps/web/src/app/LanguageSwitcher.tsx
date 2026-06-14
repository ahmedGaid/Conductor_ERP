import { useTranslation } from "react-i18next";

import { SUPPORTED_LANGUAGES, type Language } from "../i18n";
import "./LanguageSwitcher.css";

const LABEL_KEY: Record<Language, "language.arabic" | "language.english"> = {
  ar: "language.arabic",
  en: "language.english",
};

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const active = (i18n.resolvedLanguage ?? "ar") as Language;

  return (
    <div className="lang-switch" role="group" aria-label={t("language.label")}>
      {SUPPORTED_LANGUAGES.map((lng) => {
        const name = t(LABEL_KEY[lng]);
        const isActive = lng === active;
        return (
          <button
            key={lng}
            type="button"
            className="lang-switch__btn"
            aria-pressed={isActive}
            title={t("language.switchTo", { name })}
            onClick={() => void i18n.changeLanguage(lng)}
          >
            {name}
          </button>
        );
      })}
    </div>
  );
}
