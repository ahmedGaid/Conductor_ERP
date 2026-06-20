import { useTranslation } from "react-i18next";

import { usePreferences } from "../../preferences/PreferencesContext";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { FAVORITE_CANDIDATES } from "./navFavorites";

export function NavigationSettingsPage() {
  const { t } = useTranslation();
  const { prefs, update } = usePreferences();

  if (!prefs) return <SettingsSkeleton />;

  const favorites = prefs.favorites ?? [];
  const isFav = (to: string) => favorites.some((f) => f.to === to);

  function toggle(label: string, to: string) {
    const next = isFav(to)
      ? favorites.filter((f) => f.to !== to)
      : [...favorites, { label, to }];
    update({ favorites: next });
  }

  return (
    <section className="page-enter">
      <SettingsNav />
      <div className="card setcard">
        <div className="setrow setrow--block">
          <div className="setrow__label">
            <span className="setrow__title">{t("settings.nav.favoritesTitle")}</span>
            <p className="setrow__desc">{t("settings.nav.favoritesDesc")}</p>
          </div>
          <ul className="fav-list">
            {FAVORITE_CANDIDATES.map(({ label, to }) => {
              const on = isFav(to);
              return (
                <li key={to} className="fav-row">
                  <span className="fav-row__name">{t(label)}</span>
                  <button
                    type="button"
                    className={on ? "fav-star fav-star--on" : "fav-star"}
                    aria-pressed={on}
                    aria-label={t(on ? "settings.nav.unpin" : "settings.nav.pin")}
                    title={t(on ? "settings.nav.unpin" : "settings.nav.pin")}
                    onClick={() => toggle(label, to)}
                  >
                    <span aria-hidden="true">{on ? "★" : "☆"}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}
