// Backwards-compatible shim. The colour theme is now one of several presentation preferences —
// the full set lives in ./prefs. This module keeps the original light/dark helper names working.
export type { Theme } from "./prefs";
export { systemTheme, applyTheme } from "./prefs";

import { applyTheme, getThemeChoice, resolveTheme, type Theme } from "./prefs";

/** The active resolved theme (explicit choice if any, otherwise the OS preference). */
export function getTheme(): "light" | "dark" {
  return resolveTheme(getThemeChoice());
}

/** Persist an explicit choice and reflect it onto <html> immediately. */
export function setTheme(theme: Theme): void {
  applyTheme(theme);
}
