import { useCallback, useRef, type PointerEvent } from "react";
import { Trans, useTranslation } from "react-i18next";
import { HashLink } from "./HashLink";

const APP_URL = "#/login"; // HashRouter route to the live app (dev/login entry).

/**
 * The hero visual is a REAL screenshot of the running Conductor app (the Arabic, RTL dashboard with
 * live figures), framed in a browser window that tilts gently toward the pointer. Not a mock — the
 * product itself is the hero. The dark shot floating on the light page is the premium product-shot
 * pattern; it reads identically in both landing themes.
 */
function HeroProductFrame() {
  const { t } = useTranslation();
  const tiltRef = useRef<HTMLDivElement>(null);

  const onMove = useCallback((e: PointerEvent<HTMLDivElement>) => {
    const el = tiltRef.current;
    if (!el || e.pointerType !== "mouse") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    el.style.setProperty("--rx", `${(-py * 3.5).toFixed(2)}deg`);
    el.style.setProperty("--ry", `${(px * 4.5).toFixed(2)}deg`);
  }, []);

  const onLeave = useCallback(() => {
    const el = tiltRef.current;
    if (!el) return;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
  }, []);

  return (
    <div className="lp-tilt" onPointerMove={onMove} onPointerLeave={onLeave}>
      <div ref={tiltRef} className="lp-frame lp-frame--shot">
        <div className="lp-frame__bar" aria-hidden="true">
          <span className="lp-frame__dot" />
          <span className="lp-frame__dot" />
          <span className="lp-frame__dot" />
          <span className="lp-frame__url">app.conductor</span>
        </div>
        <img
          className="lp-frame__shot"
          src="/landing/shots/dash.png"
          alt={t("landing.hero.frameAlt")}
          width={1400}
          height={880}
        />
      </div>
    </div>
  );
}

/** A slow, quiet ticker of what Conductor unifies — one system, in sync. Doubled for a seamless loop. */
function SyncTicker() {
  const { t } = useTranslation();
  const items = t("landing.sync.items", { returnObjects: true }) as string[];
  const lane = [...items, ...items];
  return (
    <div className="lp-ticker" aria-label={t("landing.sync.lead")}>
      <span className="lp-ticker__lead">{t("landing.sync.lead")}</span>
      <div className="lp-ticker__mask" aria-hidden="true">
        <div className="lp-ticker__lane">
          {lane.map((label, i) => (
            <span key={i} className="lp-ticker__item">
              {label}
              <span className="lp-ticker__dot">·</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function HeroSection() {
  const { t } = useTranslation();
  return (
    <section className="lp-hero" id="top">
      <div className="lp-ambient" aria-hidden="true" />
      <div className="lp-wrap">
        <div className="lp-hero__intro">
          <span className="lp-eyebrow lp-rise" style={{ animationDelay: "40ms" }}>
            {t("landing.hero.eyebrow")}
          </span>
          <h1 className="lp-hero__title lp-rise" style={{ animationDelay: "120ms" }}>
            <Trans i18nKey="landing.hero.title" components={{ br: <br /> }} />
          </h1>
          <p className="lp-hero__lede lp-rise" style={{ animationDelay: "220ms" }}>
            {t("landing.hero.subtitle")}
          </p>
          <div className="lp-hero__cta lp-rise" style={{ animationDelay: "320ms" }}>
            <a href={APP_URL} className="lp-btn lp-btn--solid lp-btn--lg lp-btn--shine">
              {t("landing.hero.tryCta")}
            </a>
            <HashLink to="#pricing" className="lp-btn lp-btn--ghost lp-btn--lg">
              {t("landing.hero.secondaryCta")}
            </HashLink>
          </div>
          <p className="lp-hero__tryhint lp-rise" style={{ animationDelay: "400ms" }}>
            {t("landing.hero.tryHint")}
          </p>
        </div>
        <div className="lp-hero__visual lp-rise" style={{ animationDelay: "480ms" }}>
          <HeroProductFrame />
        </div>
        <div className="lp-rise" style={{ animationDelay: "620ms" }}>
          <SyncTicker />
        </div>
      </div>
    </section>
  );
}
