// Colour theme (light / dark). The theme is a single attribute on <html data-theme>; all colour
// lives in tokens.css, which remaps the semantic colour tokens under [data-theme="dark"]. The
// early inline script in index.html applies the stored/system theme before first paint (no flash);
// this module is the source of truth the ThemeToggle reads and writes at runtime.
export type Theme = "light" | "dark";

const STORAGE_KEY = "erp.theme";

export function systemTheme(): Theme {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** The active theme: an explicit user choice if set, otherwise the OS preference. */
export function getTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "dark" || stored === "light" ? stored : systemTheme();
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}

/** Persist an explicit choice and reflect it onto <html> immediately. */
export function setTheme(theme: Theme): void {
  localStorage.setItem(STORAGE_KEY, theme);
  applyTheme(theme);
}
