import { apiFetch } from "./client";

export interface Me {
  id: number;
  username: string;
  email: string;
  roles: string[];
  is_2fa_enabled: boolean;
  branch: string | null;
}

export function getMe(): Promise<Me> {
  return apiFetch<Me>("/identity/me");
}

// --- Personalization ---------------------------------------------------------------------------

export interface Preferences {
  display_name: string;
  job_title: string;
  phone: string;
  preferred_language: "" | "ar" | "en";
  time_zone: string;
  date_format: "iso" | "dmy" | "mdy";
  time_format: "24h" | "12h";
  theme: "" | "system" | "light" | "dark";
  accent_color: "" | "blue" | "black" | "green" | "purple" | "orange" | "red";
  sidebar_style: "expanded" | "compact";
  density: "comfortable" | "compact";
  font_size: "small" | "default" | "large";
  high_contrast: boolean;
  reduced_motion: boolean;
  keyboard_nav: boolean;
  notif_email: boolean;
  notif_inapp: boolean;
  notif_sound: boolean;
  notif_desktop: boolean;
  digest_frequency: "off" | "daily" | "weekly";
  default_landing: string;
  dashboard_layout: { order?: string[]; hidden?: string[] };
  favorites: { label: string; to: string }[];
  /** Org-wide feature flag merged into effective preferences (the nav reads it). */
  einvoice_enabled?: boolean;
  /** Org workspace name merged into effective preferences (the sidebar shows it). */
  company_name?: string;
  updated_at?: string;
}

export interface OrgPreferences {
  default_language: "ar" | "en";
  default_theme: "system" | "light" | "dark";
  default_accent: "blue" | "black" | "green" | "purple" | "orange" | "red";
  default_landing: string;
  company_name: string;
  country: string;
  vat_number: string;
  base_currency: string;
  einvoice_enabled: boolean;
  updated_at?: string;
}

export function getPreferences(): Promise<Preferences> {
  return apiFetch<Preferences>("/identity/preferences");
}

/** Personal preferences with org defaults filled in for blank inheritable fields. */
export function getEffectivePreferences(): Promise<Preferences> {
  return apiFetch<Preferences>("/identity/preferences/effective");
}

export function patchPreferences(changes: Partial<Preferences>): Promise<Preferences> {
  return apiFetch<Preferences>("/identity/preferences", {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export function getOrgPreferences(): Promise<OrgPreferences> {
  return apiFetch<OrgPreferences>("/identity/org-preferences");
}

export function patchOrgPreferences(changes: Partial<OrgPreferences>): Promise<OrgPreferences> {
  return apiFetch<OrgPreferences>("/identity/org-preferences", {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}
