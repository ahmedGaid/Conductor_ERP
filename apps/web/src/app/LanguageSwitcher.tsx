import { useTranslation } from "react-i18next";

import { Tooltip } from "../components/Tooltip";
import i18n, { SUPPORTED_LANGUAGES, type Language } from "../i18n";
import { usePreferencesOptional } from "../preferences/PreferencesContext";
import "./LanguageSwitcher.css";

const LABEL_KEY: Record<Language, "language.arabic" | "language.english"> = {
  ar: "language.arabic",
  en: "language.english",
};

export function LanguageSwitcher() {
  const { t } = useTranslation();
  const prefs = usePreferencesOptional();
  const active = (i18n.resolvedLanguage ?? "ar") as Language;

  // Signed in → persist to the user's server preferences so the choice survives
  // a reload (PreferencesProvider re-applies the stored language on every mount).
  // Pre-auth login screen → no provider, so just change the live UI language.
  const pick = (lng: Language) => {
    if (prefs) void prefs.update({ preferred_language: lng });
    else void i18n.changeLanguage(lng);
  };

  return (
    <div className="lang-switch" role="group" aria-label={t("language.label")}>
      {SUPPORTED_LANGUAGES.map((lng) => {
        const name = t(LABEL_KEY[lng]);
        const isActive = lng === active;
        return (
          <Tooltip key={lng} label={t("language.switchTo", { name })} placement="bottom">
            <button
              type="button"
              className="lang-switch__btn"
              aria-pressed={isActive}
              onClick={() => pick(lng)}
            >
              {name}
            </button>
          </Tooltip>
        );
      })}
    </div>
  );
}
