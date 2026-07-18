import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { useAssistant } from "../assistant/AssistantProvider";
import { Tooltip } from "../components/Tooltip";
import { SegmentedControl } from "../components/SegmentedControl";
import { NavIcon } from "../app/icons";
import { resolveGuide } from "./registry";
import { useHelp } from "./HelpContext";
import { useHelpSignals } from "./HelpSignalsContext";
import type { HelpGuide, HelpSignals, L } from "./types";
import "./help.css";

type HelpTab = "guide" | "live";
const ALERT_ICON: Record<"info" | "warn" | "success", string> = {
  info: "info",
  warn: "flag",
  success: "checkCircle",
};

/** Floating "?" button + the slide-in guide drawer. Mounted once in the app shell, so every page
 *  gets context help automatically — the guide shown is chosen from the current route. The open
 *  state lives in HelpContext so the top-bar "?" action can open the same drawer. The fab itself
 *  hides while the assistant panel is open — both anchor the same inline-end corner, so the panel
 *  would otherwise sit on top of it; the ⋮ menu's Help item still reaches the drawer either way. */
export function HelpCenter() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { open, openHelp, closeHelp, toggleHelp } = useHelp();
  const { open: assistantOpen } = useAssistant();
  const signals = useHelpSignals();
  const setOpen = (v: boolean) => (v ? openHelp() : closeHelp());

  // Pick the right language for guide content from the active locale.
  const lang: keyof L = i18n.language?.startsWith("ar") ? "ar" : "en";
  const tr = (s: L | undefined): string => (s ? s[lang] : "");

  const guide: HelpGuide | undefined = resolveGuide(location.pathname);

  // A page opts into the Live tab by publishing signals AND its guide declaring alerts/checklist.
  const activeAlerts = (guide?.alerts ?? []).filter((a) => a.when(signals));
  const hasLive = Boolean(guide && (guide.alerts?.length || guide.checklist));
  // The fab's red dot is specifically "you did something wrong, right now" — warn-tone alerts only.
  // info/success alerts (a future "here's a tip" or the checklist's done banner) don't nag the fab.
  const errorCount = activeAlerts.filter((a) => a.tone === "warn").length;

  // Which tab is showing. Default to Live when something needs attention *right now* (an alert is
  // active), otherwise the static Guide — the reference is the calm default, the live view earns
  // the front seat only when it has news. Recomputed per open via the effect below.
  const [tab, setTab] = useState<HelpTab>("guide");

  // Close the drawer on navigation and on Escape.
  useEffect(() => setOpen(false), [location.pathname]);
  // On each open, pick the tab that serves the moment: Live if it has an active alert, else Guide.
  useEffect(() => {
    if (open) setTab(hasLive && activeAlerts.length > 0 ? "live" : "guide");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
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
      {!assistantOpen && (
        <Tooltip
          label={errorCount > 0 ? t("help.buttonWithIssues", { count: errorCount }) : t("help.button")}
          placement="top"
        >
          <button
            type="button"
            className="help-fab"
            aria-haspopup="dialog"
            aria-expanded={open}
            aria-label={errorCount > 0 ? t("help.buttonWithIssues", { count: errorCount }) : t("help.button")}
            onClick={toggleHelp}
          >
            <span aria-hidden="true">?</span>
            {/* Closed-drawer signal: something on this page needs fixing right now — mirrors the
                notification bell's red-count badge so it reads as one family of "you have news". */}
            {!open && errorCount > 0 && (
              <span className="help-fab__badge" aria-hidden="true">
                {errorCount > 9 ? "9+" : errorCount}
              </span>
            )}
          </button>
        </Tooltip>
      )}

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

            {hasLive && (
              <div className="help-drawer__tabs">
                <SegmentedControl<HelpTab>
                  value={tab}
                  onChange={setTab}
                  ariaLabel={t("help.tabsLabel")}
                  options={[
                    {
                      value: "guide",
                      label: (
                        <span className="help-tab-label">
                          <NavIcon name="knowledge" />
                          {t("help.tabGuide")}
                        </span>
                      ),
                    },
                    {
                      value: "live",
                      label: (
                        <span className="help-tab-label">
                          <NavIcon name="sparkle" />
                          {t("help.tabLive")}
                          {activeAlerts.length > 0 && <span className="help-tab-dot" aria-hidden="true" />}
                        </span>
                      ),
                    },
                  ]}
                />
              </div>
            )}

            <div className="help-drawer__body">
              {!guide && <p className="help-empty">{t("help.noGuide")}</p>}

              {guide && hasLive && tab === "live" && (
                <LiveTab
                  guide={guide}
                  signals={signals}
                  activeAlerts={activeAlerts}
                  lang={lang}
                  tr={tr}
                  t={t}
                />
              )}

              {guide && (!hasLive || tab === "guide") && (
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

/** The Live tab: page-state alerts pinned on top, then a checklist whose steps tick themselves off
 *  as the page's published signals report each one done. Both read `signals`, never self-report. */
function LiveTab({
  guide,
  signals,
  activeAlerts,
  lang,
  tr,
  t,
}: {
  guide: HelpGuide;
  signals: HelpSignals;
  activeAlerts: NonNullable<HelpGuide["alerts"]>;
  lang: keyof L;
  tr: (s: L | undefined) => string;
  t: (key: string) => string;
}) {
  const checklist = guide.checklist;
  const doneCount = checklist ? checklist.steps.filter((s) => s.done(signals)).length : 0;

  return (
    <>
      {activeAlerts.length === 0 && !checklist && (
        <p className="help-empty">{t("help.live.calm")}</p>
      )}

      {activeAlerts.map((alert, idx) => (
        <div className={`help-alert help-alert--${alert.tone}`} key={idx} role="status">
          <span className="help-alert__icon" aria-hidden="true">
            <NavIcon name={ALERT_ICON[alert.tone]} />
          </span>
          <div className="help-alert__text">
            <p className="help-alert__title">{tr(alert.title)}</p>
            <p className="help-alert__body">{tr(alert.body)}</p>
          </div>
        </div>
      ))}

      {checklist && (
        <section className="help-block">
          <h3 className="help-block__title">
            {tr(checklist.name)}
            <span className="help-checklist__count">
              {doneCount}/{checklist.steps.length}
            </span>
          </h3>
          {/* A thin progress bar so "how far am I" reads at a glance. */}
          <div className="help-progress" aria-hidden="true">
            <div
              className="help-progress__fill"
              style={{ inlineSize: `${(doneCount / checklist.steps.length) * 100}%` }}
            />
          </div>
          <ol className="help-checklist">
            {checklist.steps.map((step, idx) => {
              const done = step.done(signals);
              // The first not-yet-done step is the one to do next — expand it, dim the ones after.
              const isNext = !done && checklist.steps.slice(0, idx).every((s) => s.done(signals));
              const cls = done
                ? "help-checkstep help-checkstep--done"
                : isNext
                  ? "help-checkstep help-checkstep--next"
                  : "help-checkstep help-checkstep--todo";
              return (
                <li className={cls} key={idx}>
                  <div className="help-checkstep__row">
                    <span className="help-checkstep__icon" aria-hidden="true">
                      <NavIcon name={done ? "checkCircle" : isNext ? "arrowBack" : "clock"} />
                    </span>
                    <span className="help-checkstep__label">{step.label[lang]}</span>
                  </div>
                  {/* Lead the user through the current step, one micro-action at a time. */}
                  {isNext && step.detail && step.detail.length > 0 && (
                    <ol className="help-checkstep__detail">
                      {step.detail.map((d, j) => (
                        <li key={j}>{d[lang]}</li>
                      ))}
                    </ol>
                  )}
                  {done && step.hint && <p className="help-checkstep__hint">{step.hint[lang]}</p>}
                </li>
              );
            })}
          </ol>
          {doneCount === checklist.steps.length && checklist.doneMessage && (
            <div className="help-alert help-alert--success" role="status">
              <span className="help-alert__icon" aria-hidden="true">
                <NavIcon name="checkCircle" />
              </span>
              <div className="help-alert__text">
                <p className="help-alert__body">{tr(checklist.doneMessage)}</p>
              </div>
            </div>
          )}
        </section>
      )}
    </>
  );
}
