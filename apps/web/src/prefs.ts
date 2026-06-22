// Presentation preferences — the single runtime source of truth for the personalization the user
// sets in Settings. Each preference is applied as an independent attribute on <html data-*>; the
// colour/spacing/type tokens remap under those attributes in tokens.css, so a change flips the whole
// app with no per-component code. Every applied value is cached to localStorage under the same key
// the early inline script in index.html reads, so the look survives a reload with no flash (no-FOUC).
//
// Only in-page accent recolours with `accent` — the near-black app chrome (brand/buttons/logo/active
// nav) is intentionally fixed (see DECISIONS), so accent only remaps the --color-accent* family.

export type Theme = "system" | "light" | "dark";
export type Accent = "blue" | "black" | "green" | "purple" | "orange" | "red";
export type Density = "comfortable" | "compact";
export type FontSize = "small" | "default" | "large";
export type SidebarStyle = "expanded" | "compact";

export const ACCENTS: Accent[] = ["blue", "black", "green", "purple", "orange", "red"];

const KEY = {
  theme: "erp.theme",
  accent: "erp.accent",
  density: "erp.density",
  fontSize: "erp.fontSize",
  contrast: "erp.contrast",
  motion: "erp.motion",
  sidebar: "erp.sidebar",
} as const;

export function systemTheme(): "light" | "dark" {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** The concrete light/dark to paint for a (possibly "system") theme choice. */
export function resolveTheme(theme: Theme): "light" | "dark" {
  return theme === "light" || theme === "dark" ? theme : systemTheme();
}

/** The stored theme *choice* ("system" by default), as opposed to the resolved light/dark. */
export function getThemeChoice(): Theme {
  const s = localStorage.getItem(KEY.theme);
  return s === "light" || s === "dark" || s === "system" ? s : "system";
}

// --- per-field appliers: set the <html> attribute + cache for no-FOUC ---

export function applyTheme(theme: Theme): void {
  localStorage.setItem(KEY.theme, theme);
  document.documentElement.setAttribute("data-theme", resolveTheme(theme));
}

export function applyAccent(accent: string): void {
  const value = accent || "blue";
  localStorage.setItem(KEY.accent, value);
  document.documentElement.setAttribute("data-accent", value);
}

export function applyDensity(density: string): void {
  const value = density || "comfortable";
  localStorage.setItem(KEY.density, value);
  document.documentElement.setAttribute("data-density", value);
}

export function applyFontSize(size: string): void {
  const value = size || "default";
  localStorage.setItem(KEY.fontSize, value);
  document.documentElement.setAttribute("data-font-size", value);
}

export function applyContrast(high: boolean): void {
  const value = high ? "high" : "normal";
  localStorage.setItem(KEY.contrast, value);
  document.documentElement.setAttribute("data-contrast", value);
}

export function applyMotion(reduced: boolean): void {
  const value = reduced ? "reduced" : "full";
  localStorage.setItem(KEY.motion, value);
  document.documentElement.setAttribute("data-motion", value);
}

export function applySidebarStyle(style: string): void {
  const value = style || "expanded";
  localStorage.setItem(KEY.sidebar, value);
  document.documentElement.setAttribute("data-sidebar", value);
}

/** The subset of a (effective) preferences payload that maps to the document. */
export interface AppliedPreferences {
  theme?: string;
  accent_color?: string;
  density?: string;
  font_size?: string;
  high_contrast?: boolean;
  reduced_motion?: boolean;
  sidebar_style?: string;
}

/** Apply every presentation field present in the payload to <html>. */
export function applyPreferences(p: AppliedPreferences): void {
  if (p.theme !== undefined) applyTheme((p.theme || "system") as Theme);
  if (p.accent_color !== undefined) applyAccent(p.accent_color);
  if (p.density !== undefined) applyDensity(p.density);
  if (p.font_size !== undefined) applyFontSize(p.font_size);
  if (p.high_contrast !== undefined) applyContrast(p.high_contrast);
  if (p.reduced_motion !== undefined) applyMotion(p.reduced_motion);
  if (p.sidebar_style !== undefined) applySidebarStyle(p.sidebar_style);
}
