import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import ar from "./locales/ar.json";
import en from "./locales/en.json";

export const SUPPORTED_LANGUAGES = ["ar", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

/** Right-to-left languages. Arabic is the product default. */
const RTL_LANGUAGES: ReadonlySet<string> = new Set(["ar"]);

export function directionFor(language: string): "rtl" | "ltr" {
  return RTL_LANGUAGES.has(language) ? "rtl" : "ltr";
}

/** Reflect the active language onto <html lang/dir> so logical CSS mirrors live. */
export function applyDocumentLanguage(language: string): void {
  const root = document.documentElement;
  root.setAttribute("lang", language);
  root.setAttribute("dir", directionFor(language));
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      ar: { translation: ar },
      en: { translation: en },
    },
    // Arabic / RTL is the default experience.
    fallbackLng: "ar",
    supportedLngs: [...SUPPORTED_LANGUAGES],
    nonExplicitSupportedLngs: true,
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "erp.lang",
      caches: ["localStorage"],
    },
  });

// Keep <html> in sync on load and on every change.
applyDocumentLanguage(i18n.resolvedLanguage ?? "ar");
i18n.on("languageChanged", (lng) => applyDocumentLanguage(lng));

export default i18n;
