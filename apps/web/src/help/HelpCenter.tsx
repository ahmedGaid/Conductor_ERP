import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { resolveGuide } from "./registry";
import type { HelpGuide, L } from "./types";
import "./help.css";

/** Floating "?" button + the slide-in guide drawer. Mounted once in the app shell, so every page
 *  gets context help automatically — the guide shown is chosen from the current route. */
export function HelpCenter() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  // Pick the right language for guide content from the active locale.
  const lang: keyof L = i18n.language?.startsWith("ar") ? "ar" : "en";
  const tr = (s: L | undefined): string => (s ? s[lang] : "");

  const guide: HelpGuide | undefined = resolveGuide(location.pathname);

  // Close the drawer on navigation and on Escape.
  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function goTo(to: string) {
    setOpen(false);
    navigate(to);
  }

  return (
    <>
      <button
        type="button"
        className="help-fab"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={t("help.button")}
        title={t("help.button")}
        onClick={() => setOpen((v) => !v)}
      >
        <span aria-hidden="true">?</span>
      </button>

      {open && (
        <>
          <button
            type="button"
            className="help-scrim"
            aria-label={t("help.close")}
            onClick={() => setOpen(false)}
          />
          <aside className="help-drawer" role="dialog" aria-modal="true" aria-label={t("help.button")}>
            <header className="help-drawer__head">
              <h2 className="help-drawer__title">{guide ? tr(guide.title) : t("help.button")}</h2>
              <button
                type="button"
                className="help-drawer__close"
                aria-label={t("help.close")}
                onClick={() => setOpen(false)}
              >
                <span aria-hidden="true">×</span>
              </button>
            </header>

            <div className="help-drawer__body">
              {!guide && <p className="help-empty">{t("help.noGuide")}</p>}

              {guide && (
                <>
                  <section className="help-block">
                    <h3 className="help-block__title">{t("help.purpose")}</h3>
                    <p>{tr(guide.purpose)}</p>
                  </section>

                  <section className="help-block">
                    <h3 className="help-block__title">{t("help.howItWorks")}</h3>
                    <p>{tr(guide.howItWorks)}</p>
                  </section>

                  {guide.sections && guide.sections.length > 0 && (
                    <section className="help-block">
                      <h3 className="help-block__title">{t("help.onThisPage")}</h3>
                      {guide.sections.map((s, idx) => (
                        <div className="help-section" key={idx}>
                          <h4 className="help-section__heading">{tr(s.heading)}</h4>
                          {s.body && <p>{tr(s.body)}</p>}
                          {s.items && s.items.length > 0 && (
                            <dl className="help-deflist">
                              {s.items.map((it, j) => (
                                <div className="help-deflist__row" key={j}>
                                  <dt>{tr(it.term)}</dt>
                                  <dd>{tr(it.desc)}</dd>
                                </div>
                              ))}
                            </dl>
                          )}
                        </div>
                      ))}
                    </section>
                  )}

                  {guide.tasks && guide.tasks.length > 0 && (
                    <section className="help-block">
                      <h3 className="help-block__title">{t("help.tasks")}</h3>
                      {guide.tasks.map((task, idx) => (
                        <div className="help-task" key={idx}>
                          <h4 className="help-section__heading">{tr(task.name)}</h4>
                          <ol className="help-steps">
                            {task.steps.map((step, j) => (
                              <li key={j}>{step[lang]}</li>
                            ))}
                          </ol>
                        </div>
                      ))}
                    </section>
                  )}

                  {guide.examples && guide.examples.length > 0 && (
                    <section className="help-block">
                      <h3 className="help-block__title">{t("help.examples")}</h3>
                      <ul className="help-list">
                        {guide.examples.map((ex, idx) => (
                          <li key={idx}>{ex[lang]}</li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {guide.tips && guide.tips.length > 0 && (
                    <section className="help-block">
                      <h3 className="help-block__title">{t("help.tips")}</h3>
                      <ul className="help-list help-list--tips">
                        {guide.tips.map((tip, idx) => (
                          <li key={idx}>{tip[lang]}</li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {guide.mistakes && guide.mistakes.length > 0 && (
                    <section className="help-block">
                      <h3 className="help-block__title">{t("help.mistakes")}</h3>
                      <ul className="help-list help-list--mistakes">
                        {guide.mistakes.map((m, idx) => (
                          <li key={idx}>{m[lang]}</li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {guide.related && guide.related.length > 0 && (
                    <section className="help-block">
                      <h3 className="help-block__title">{t("help.related")}</h3>
                      <ul className="help-links">
                        {guide.related.map((link, idx) => (
                          <li key={idx}>
                            <button type="button" className="help-link" onClick={() => goTo(link.to)}>
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
          </aside>
        </>
      )}
    </>
  );
}
