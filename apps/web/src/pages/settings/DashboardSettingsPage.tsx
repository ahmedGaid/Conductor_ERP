import { useTranslation } from "react-i18next";

import { usePreferences } from "../../preferences/PreferencesContext";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { SettingRow, Toggle } from "./controls";
import { DASHBOARD_WIDGETS } from "./dashboardWidgets";

const LANDING_OPTIONS = ["/", "/sales", "/purchasing", "/inventory", "/accounting", "/crm", "/workflows"];

export function DashboardSettingsPage() {
  const { t } = useTranslation();
  const { prefs, update } = usePreferences();

  if (!prefs) return <SettingsSkeleton />;

  const layout = prefs.dashboard_layout ?? {};
  const keys = DASHBOARD_WIDGETS.map((w) => w.key);
  const order = [
    ...(layout.order ?? []).filter((k) => keys.includes(k)),
    ...keys.filter((k) => !(layout.order ?? []).includes(k)),
  ];
  const hidden = new Set(layout.hidden ?? []);
  const labelOf = (key: string) =>
    t(DASHBOARD_WIDGETS.find((w) => w.key === key)!.labelKey);

  function persist(nextOrder: string[], nextHidden: Set<string>) {
    update({ dashboard_layout: { order: nextOrder, hidden: [...nextHidden] } });
  }

  function move(key: string, delta: number) {
    const i = order.indexOf(key);
    const j = i + delta;
    if (j < 0 || j >= order.length) return;
    const next = [...order];
    [next[i], next[j]] = [next[j], next[i]];
    persist(next, hidden);
  }

  function toggleVisible(key: string, visible: boolean) {
    const next = new Set(hidden);
    if (visible) next.delete(key);
    else next.add(key);
    persist(order, next);
  }

  return (
    <section className="page-enter">
      <SettingsNav />
      <div className="card setcard">
        <SettingRow
          title={t("settings.dashboard.landing")}
          desc={t("settings.dashboard.landingDesc")}
          htmlFor="ds-landing"
        >
          <select
            id="ds-landing"
            value={prefs.default_landing || "/"}
            onChange={(e) => update({ default_landing: e.target.value })}
          >
            {LANDING_OPTIONS.map((to) => (
              <option key={to} value={to}>
                {t(`settings.dashboard.landingOptions.${to === "/" ? "dashboard" : to.slice(1)}`)}
              </option>
            ))}
          </select>
        </SettingRow>

        <div className="setrow setrow--block">
          <div className="setrow__label">
            <span className="setrow__title">{t("settings.dashboard.widgetsTitle")}</span>
            <p className="setrow__desc">{t("settings.dashboard.widgetsDesc")}</p>
          </div>
          <ul className="widget-list">
            {order.map((key, i) => (
              <li key={key} className="widget-row">
                <span className="widget-row__name">{labelOf(key)}</span>
                <div className="widget-row__actions">
                  <button
                    type="button"
                    className="btn btn--ghost btn--icon"
                    aria-label={t("settings.dashboard.moveUp")}
                    disabled={i === 0}
                    onClick={() => move(key, -1)}
                  >
                    <span aria-hidden="true">↑</span>
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--icon"
                    aria-label={t("settings.dashboard.moveDown")}
                    disabled={i === order.length - 1}
                    onClick={() => move(key, 1)}
                  >
                    <span aria-hidden="true">↓</span>
                  </button>
                  <Toggle
                    label={t("settings.dashboard.show")}
                    checked={!hidden.has(key)}
                    onChange={(on) => toggleVisible(key, on)}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
