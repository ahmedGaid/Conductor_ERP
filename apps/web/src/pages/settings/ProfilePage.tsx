import { useTranslation } from "react-i18next";

import { getMe } from "../../api/identity";
import { useAsync } from "../../hooks/useAsync";
import { usePreferences } from "../../preferences/PreferencesContext";
import { SettingsNav } from "./SettingsNav";
import { Segmented, SettingRow } from "./controls";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2);
  return letters.toUpperCase();
}

export function ProfilePage() {
  const { t } = useTranslation();
  const { prefs, update } = usePreferences();
  const { data: me } = useAsync(getMe, []);

  if (!prefs) return <SettingsSkeleton />;
  const shownName = prefs.display_name || me?.username || "?";

  return (
    <section className="page-enter">
      <SettingsNav />
      <div className="card setcard">
        <div className="profile-id">
          <span className="profile-id__avatar" aria-hidden="true">
            {initials(shownName)}
          </span>
          <div className="profile-id__meta">
            <span className="profile-id__name">{shownName}</span>
            <span className="profile-id__email latin">{me?.email ?? "—"}</span>
          </div>
        </div>

        <SettingRow title={t("settings.profile.displayName")} htmlFor="pf-name">
          <input
            id="pf-name"
            type="text"
            value={prefs.display_name}
            onChange={(e) => update({ display_name: e.target.value })}
            placeholder={me?.username ?? ""}
          />
        </SettingRow>
        <SettingRow title={t("settings.profile.jobTitle")} htmlFor="pf-job">
          <input
            id="pf-job"
            type="text"
            value={prefs.job_title}
            onChange={(e) => update({ job_title: e.target.value })}
          />
        </SettingRow>
        <SettingRow title={t("settings.profile.phone")} htmlFor="pf-phone">
          <input
            id="pf-phone"
            type="tel"
            className="latin"
            value={prefs.phone}
            onChange={(e) => update({ phone: e.target.value })}
          />
        </SettingRow>

        <SettingRow title={t("settings.profile.language")} desc={t("settings.profile.languageDesc")}>
          <Segmented
            ariaLabel={t("settings.profile.language")}
            value={prefs.preferred_language}
            onChange={(v) => update({ preferred_language: v })}
            options={[
              { value: "", label: t("settings.common.auto") },
              { value: "ar", label: "العربية" },
              { value: "en", label: "English" },
            ]}
          />
        </SettingRow>
        <SettingRow title={t("settings.profile.timeZone")} htmlFor="pf-tz">
          <input
            id="pf-tz"
            type="text"
            className="latin"
            value={prefs.time_zone}
            onChange={(e) => update({ time_zone: e.target.value })}
          />
        </SettingRow>
        <SettingRow title={t("settings.profile.dateFormat")}>
          <Segmented
            ariaLabel={t("settings.profile.dateFormat")}
            value={prefs.date_format}
            onChange={(v) => update({ date_format: v })}
            options={[
              { value: "iso", label: "2026-06-20" },
              { value: "dmy", label: "20/06/2026" },
              { value: "mdy", label: "06/20/2026" },
            ]}
          />
        </SettingRow>
        <SettingRow title={t("settings.profile.timeFormat")}>
          <Segmented
            ariaLabel={t("settings.profile.timeFormat")}
            value={prefs.time_format}
            onChange={(v) => update({ time_format: v })}
            options={[
              { value: "24h", label: t("settings.profile.h24") },
              { value: "12h", label: t("settings.profile.h12") },
            ]}
          />
        </SettingRow>
      </div>
    </section>
  );
}

export function SettingsSkeleton() {
  return (
    <section>
      <SettingsNav />
      <div className="card setcard">
        <div className="page-skeleton">
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
          <span className="skeleton skeleton--row" />
        </div>
      </div>
    </section>
  );
}
