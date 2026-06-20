import { useTranslation } from "react-i18next";

import { usePreferences } from "../../preferences/PreferencesContext";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { SettingRow, Toggle } from "./controls";

export function AccessibilityPage() {
  const { t } = useTranslation();
  const { prefs, update } = usePreferences();

  if (!prefs) return <SettingsSkeleton />;

  return (
    <section className="page-enter">
      <SettingsNav />
      <div className="card setcard">
        <SettingRow title={t("settings.a11y.largerText")} desc={t("settings.a11y.largerTextDesc")}>
          <Toggle
            label={t("settings.a11y.largerText")}
            checked={prefs.font_size === "large"}
            onChange={(on) => update({ font_size: on ? "large" : "default" })}
          />
        </SettingRow>
        <SettingRow title={t("settings.a11y.highContrast")} desc={t("settings.a11y.highContrastDesc")}>
          <Toggle
            label={t("settings.a11y.highContrast")}
            checked={prefs.high_contrast}
            onChange={(on) => update({ high_contrast: on })}
          />
        </SettingRow>
        <SettingRow title={t("settings.a11y.reducedMotion")} desc={t("settings.a11y.reducedMotionDesc")}>
          <Toggle
            label={t("settings.a11y.reducedMotion")}
            checked={prefs.reduced_motion}
            onChange={(on) => update({ reduced_motion: on })}
          />
        </SettingRow>
        <SettingRow title={t("settings.a11y.keyboardNav")} desc={t("settings.a11y.keyboardNavDesc")}>
          <Toggle
            label={t("settings.a11y.keyboardNav")}
            checked={prefs.keyboard_nav}
            onChange={(on) => update({ keyboard_nav: on })}
          />
        </SettingRow>
      </div>
    </section>
  );
}
