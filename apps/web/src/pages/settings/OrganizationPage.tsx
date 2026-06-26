import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  getMe,
  getOrgPreferences,
  patchOrgPreferences,
  type OrgPreferences,
} from "../../api/identity";
import { ACCENTS } from "../../prefs";
import { Tooltip } from "../../components/Tooltip";
import { useAsync } from "../../hooks/useAsync";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { SYSTEM_ADMIN } from "./roles";
import { Segmented, SettingRow } from "./controls";

const LANDING_OPTIONS = ["/", "/sales", "/purchasing", "/inventory", "/accounting", "/crm", "/workflows"];

export function OrganizationPage() {
  const { t } = useTranslation();
  const { data: me } = useAsync(getMe, []);
  const { data: loaded } = useAsync(getOrgPreferences, []);
  const [org, setOrg] = useState<OrgPreferences | null>(null);

  useEffect(() => {
    if (loaded) setOrg(loaded);
  }, [loaded]);

  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  if (me && !isAdmin) {
    return (
      <section className="page-enter">
        <SettingsNav />
        <div className="card setcard">
          <p className="muted">{t("settings.org.adminOnly")}</p>
        </div>
      </section>
    );
  }
  if (!org) return <SettingsSkeleton />;

  function save(changes: Partial<OrgPreferences>) {
    setOrg((cur) => (cur ? { ...cur, ...changes } : cur));
    patchOrgPreferences(changes).then((saved) => setOrg(saved)).catch(() => {});
  }

  return (
    <section className="page-enter">
      <SettingsNav />
      <div className="card setcard">
        <p className="setrow__desc setcard__lead">{t("settings.org.lead")}</p>

        <SettingRow title={t("settings.org.companyName")} htmlFor="org-name">
          <input
            id="org-name"
            type="text"
            value={org.company_name}
            onChange={(e) => save({ company_name: e.target.value })}
          />
        </SettingRow>

        <SettingRow title={t("settings.org.country")} htmlFor="org-country">
          <input
            id="org-country"
            type="text"
            value={org.country}
            onChange={(e) => save({ country: e.target.value })}
          />
        </SettingRow>

        <SettingRow title={t("settings.org.vatNumber")} desc={t("settings.org.vatNumberDesc")} htmlFor="org-vat">
          <input
            id="org-vat"
            type="text"
            inputMode="numeric"
            value={org.vat_number}
            onChange={(e) => save({ vat_number: e.target.value })}
          />
        </SettingRow>

        <SettingRow title={t("settings.org.baseCurrency")} desc={t("settings.org.baseCurrencyDesc")}>
          <span className="muted">{org.base_currency}</span>
        </SettingRow>

        <SettingRow title={t("settings.org.language")} desc={t("settings.org.languageDesc")}>
          <Segmented
            ariaLabel={t("settings.org.language")}
            value={org.default_language}
            onChange={(v) => save({ default_language: v })}
            options={[
              { value: "ar", label: "العربية" },
              { value: "en", label: "English" },
            ]}
          />
        </SettingRow>

        <SettingRow title={t("settings.org.theme")} desc={t("settings.org.themeDesc")}>
          <Segmented
            ariaLabel={t("settings.org.theme")}
            value={org.default_theme}
            onChange={(v) => save({ default_theme: v })}
            options={[
              { value: "light", label: t("settings.appearance.light") },
              { value: "dark", label: t("settings.appearance.dark") },
              { value: "system", label: t("settings.appearance.system") },
            ]}
          />
        </SettingRow>

        <SettingRow title={t("settings.org.accent")} desc={t("settings.org.accentDesc")}>
          <div className="swatches" role="radiogroup" aria-label={t("settings.org.accent")}>
            {ACCENTS.map((a) => (
              <Tooltip key={a} label={t(`settings.appearance.accents.${a}`)} placement="top">
                <button
                  type="button"
                  role="radio"
                  aria-checked={org.default_accent === a}
                  aria-label={t(`settings.appearance.accents.${a}`)}
                  className={org.default_accent === a ? "swatch swatch--on" : "swatch"}
                  data-accent-dot={a}
                  onClick={() => save({ default_accent: a })}
                />
              </Tooltip>
            ))}
          </div>
        </SettingRow>

        <SettingRow title={t("settings.org.landing")} desc={t("settings.org.landingDesc")} htmlFor="org-landing">
          <select
            id="org-landing"
            value={org.default_landing || "/"}
            onChange={(e) => save({ default_landing: e.target.value })}
          >
            {LANDING_OPTIONS.map((to) => (
              <option key={to} value={to}>
                {t(`settings.dashboard.landingOptions.${to === "/" ? "dashboard" : to.slice(1)}`)}
              </option>
            ))}
          </select>
        </SettingRow>
      </div>
    </section>
  );
}
