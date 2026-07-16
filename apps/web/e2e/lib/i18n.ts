// Selectors read the SAME translation strings the app renders, so a spec works unmodified in
// both the ar and en projects (see playwright.config.ts) instead of hard-coding either language.
import ar from "../../src/i18n/locales/ar.json" with { type: "json" };
import en from "../../src/i18n/locales/en.json" with { type: "json" };

export type Locale = "ar" | "en";

const DICTS: Record<Locale, unknown> = { ar, en };

/** Look up a dotted i18n key (e.g. "sales.detail.confirm") in the given locale's resource file. */
export function tFor(locale: Locale) {
  return function t(path: string): string {
    const value = path.split(".").reduce<unknown>((node, key) => {
      if (node && typeof node === "object" && key in (node as Record<string, unknown>)) {
        return (node as Record<string, unknown>)[key];
      }
      return undefined;
    }, DICTS[locale]);
    if (typeof value !== "string") {
      throw new Error(`e2e selector: missing i18n key "${path}" for locale "${locale}"`);
    }
    return value;
  };
}
