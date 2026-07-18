import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { GLOSSARY } from "../help/content/glossary";
import { JOURNEYS, getJourney } from "../help/content/journeys";
import type { L } from "../help/types";
import "../help/help.css";
import "./UserGuidePage.css";

const GLOSSARY_ID = "glossary";

/** The standalone, task-based User Guide (twenty-harvest FILE_15) — distinct from the per-page
 *  contextual Help drawer (`HelpCenter`). Reached via the "⋮" menu's "User Guide" item or a ⌘K
 *  "Help: <journey>" entry; works fully offline (no network calls, no images — everything here is
 *  bundled TS content, same pattern as the contextual guides). */
export function UserGuidePage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { journeyId } = useParams<{ journeyId?: string }>();
  const lang: keyof L = i18n.language?.startsWith("ar") ? "ar" : "en";
  const tr = (s: L): string => s[lang];

  const showGlossary = journeyId === GLOSSARY_ID;
  const active = !showGlossary ? getJourney(journeyId ?? "") ?? JOURNEYS[0] : undefined;

  function go(id: string) {
    navigate(`/help/guide/${id}`);
  }

  return (
    <section className="page-enter userguide">
      <header className="module-head">
        <h1 className="module-head__title">{t("userGuide.title")}</h1>
        <p className="module-head__desc">{t("userGuide.subtitle")}</p>
      </header>

      <div className="userguide-layout">
        <nav className="userguide-nav" aria-label={t("userGuide.title")}>
          <ul className="userguide-nav__list">
            {JOURNEYS.map((j) => (
              <li key={j.id}>
                <button
                  type="button"
                  className={
                    active?.id === j.id ? "userguide-nav__item userguide-nav__item--active" : "userguide-nav__item"
                  }
                  aria-current={active?.id === j.id ? "page" : undefined}
                  onClick={() => go(j.id)}
                >
                  {tr(j.title)}
                </button>
              </li>
            ))}
          </ul>
          <div className="userguide-nav__sep" role="separator" />
          <button
            type="button"
            className={
              showGlossary ? "userguide-nav__item userguide-nav__item--active" : "userguide-nav__item"
            }
            aria-current={showGlossary ? "page" : undefined}
            onClick={() => go(GLOSSARY_ID)}
          >
            {t("userGuide.glossaryNav")}
          </button>
        </nav>

        <div className="card userguide-content">
          {showGlossary && (
            <>
              <h2 className="help-block__title">{t("userGuide.glossaryTitle")}</h2>
              <dl className="help-deflist">
                {GLOSSARY.map((g, idx) => (
                  <div className="help-deflist__row" key={idx}>
                    <dt>{tr(g.term)}</dt>
                    <dd>{tr(g.desc)}</dd>
                  </div>
                ))}
              </dl>
            </>
          )}

          {active && (
            <>
              <h2 className="userguide-content__title">{tr(active.title)}</h2>
              <p className="userguide-content__summary">{tr(active.summary)}</p>

              <section className="help-block">
                <h3 className="help-block__title">{t("help.tasks")}</h3>
                <ol className="help-steps">
                  {active.steps.map((step, idx) => (
                    <li key={idx}>{tr(step)}</li>
                  ))}
                </ol>
              </section>

              {active.pitfalls && active.pitfalls.length > 0 && (
                <section className="help-block">
                  <h3 className="help-block__title">{t("userGuide.pitfalls")}</h3>
                  <dl className="help-deflist">
                    {active.pitfalls.map((p, idx) => (
                      <div className="help-deflist__row" key={idx}>
                        <dt>{tr(p.problem)}</dt>
                        <dd>{tr(p.fix)}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              )}

              {active.related && active.related.length > 0 && (
                <section className="help-block">
                  <h3 className="help-block__title">{t("help.related")}</h3>
                  <ul className="help-links">
                    {active.related.map((link, idx) => (
                      <li key={idx}>
                        <button type="button" className="help-link" onClick={() => navigate(link.to)}>
                          {tr(link.label)}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
