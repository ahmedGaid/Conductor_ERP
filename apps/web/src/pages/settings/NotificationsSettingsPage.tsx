import { useTranslation } from "react-i18next";

import { usePreferences } from "../../preferences/PreferencesContext";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { Segmented, SettingRow, Toggle } from "./controls";

export function NotificationsSettingsPage() {
  const { t } = useTranslation();
  const { prefs, update } = usePreferences();

  if (!prefs) return <SettingsSkeleton />;

  return (
    <section className="page-enter">
      <SettingsNav />
      <div className="card setcard">
        <SettingRow title={t("settings.notif.inapp")} desc={t("settings.notif.inappDesc")}>
          <Toggle
            label={t("settings.notif.inapp")}
            checked={prefs.notif_inapp}
            onChange={(on) => update({ notif_inapp: on })}
          />
        </SettingRow>
        <SettingRow title={t("settings.notif.email")} desc={t("settings.notif.emailDesc")}>
          <Toggle
            label={t("settings.notif.email")}
            checked={prefs.notif_email}
            onChange={(on) => update({ notif_email: on })}
          />
        </SettingRow>
        <SettingRow title={t("settings.notif.sound")} desc={t("settings.notif.soundDesc")}>
          <Toggle
            label={t("settings.notif.sound")}
            checked={prefs.notif_sound}
            onChange={(on) => update({ notif_sound: on })}
          />
        </SettingRow>
        <SettingRow title={t("settings.notif.desktop")} desc={t("settings.notif.desktopDesc")}>
          <Toggle
            label={t("settings.notif.desktop")}
            checked={prefs.notif_desktop}
            onChange={(on) => update({ notif_desktop: on })}
          />
        </SettingRow>
        <SettingRow title={t("settings.notif.digest")} desc={t("settings.notif.digestDesc")}>
          <Segmented
            ariaLabel={t("settings.notif.digest")}
            value={prefs.digest_frequency}
            onChange={(v) => update({ digest_frequency: v })}
            options={[
              { value: "off", label: t("settings.notif.off") },
              { value: "daily", label: t("settings.notif.daily") },
              { value: "weekly", label: t("settings.notif.weekly") },
            ]}
          />
        </SettingRow>
      </div>
    </section>
  );
}
