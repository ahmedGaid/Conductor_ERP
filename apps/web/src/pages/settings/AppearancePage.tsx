import { useTranslation } from "react-i18next";

import { usePreferences } from "../../preferences/PreferencesContext";
import { ACCENTS } from "../../prefs";
import { Tooltip } from "../../components/Tooltip";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { Segmented, SettingRow } from "./controls";

export function AppearancePage() {
  const { t } = useTranslation();
  const { prefs, update } = usePreferences();

  if (!prefs) return <SettingsSkeleton />;

  return (
    <section className="page-enter">
      <SettingsNav />
      <div className="card setcard">
        <SettingRow title={t("settings.appearance.theme")} desc={t("settings.appearance.themeDesc")}>
          <Segmented
            ariaLabel={t("settings.appearance.theme")}
            value={prefs.theme || "system"}
            onChange={(v) => update({ theme: v })}
            options={[
              { value: "light", label: t("settings.appearance.light") },
              { value: "dark", label: t("settings.appearance.dark") },
              { value: "system", label: t("settings.appearance.system") },
            ]}
          />
        </SettingRow>

        <SettingRow title={t("settings.appearance.accent")} desc={t("settings.appearance.accentDesc")}>
          <div className="swatches" role="radiogroup" aria-label={t("settings.appearance.accent")}>
            {ACCENTS.map((a) => {
              const active = (prefs.accent_color || "blue") === a;
              return (
                <Tooltip key={a} label={t(`settings.appearance.accents.${a}`)} placement="top">
                  <button
                    type="button"
                    role="radio"
                    aria-checked={active}
                    aria-label={t(`settings.appearance.accents.${a}`)}
                    className={active ? "swatch swatch--on" : "swatch"}
                    data-accent-dot={a}
                    onClick={() => update({ accent_color: a })}
                  />
                </Tooltip>
              );
            })}
          </div>
        </SettingRow>

        <SettingRow title={t("settings.appearance.density")} desc={t("settings.appearance.densityDesc")}>
          <Segmented
            ariaLabel={t("settings.appearance.density")}
            value={prefs.density}
            onChange={(v) => update({ density: v })}
            options={[
              { value: "comfortable", label: t("settings.appearance.comfortable") },
              { value: "compact", label: t("settings.appearance.compact") },
            ]}
          />
        </SettingRow>

        <SettingRow title={t("settings.appearance.fontSize")} desc={t("settings.appearance.fontSizeDesc")}>
          <Segmented
            ariaLabel={t("settings.appearance.fontSize")}
            value={prefs.font_size}
            onChange={(v) => update({ font_size: v })}
            options={[
              { value: "small", label: t("settings.appearance.small") },
              { value: "default", label: t("settings.appearance.default") },
              { value: "large", label: t("settings.appearance.large") },
            ]}
          />
        </SettingRow>

        <SettingRow title={t("settings.appearance.sidebar")} desc={t("settings.appearance.sidebarDesc")}>
          <Segmented
            ariaLabel={t("settings.appearance.sidebar")}
            value={prefs.sidebar_style}
            onChange={(v) => update({ sidebar_style: v })}
            options={[
              { value: "expanded", label: t("settings.appearance.expanded") },
              { value: "compact", label: t("settings.appearance.compactSidebar") },
            ]}
          />
        </SettingRow>
      </div>
    </section>
  );
}
