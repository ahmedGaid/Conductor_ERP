import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { HashLink } from "./HashLink";
import { BrandMark } from "./BrandMark";
import { LanguageSwitcher } from "../../app/LanguageSwitcher";
import { NavIcon } from "../../app/icons";

/**
 * Public marketing nav. Monochrome chrome (brand rule): the real logo mark + wordmark, quiet
 * section links, a theme toggle, and a solid primary CTA into the app. Becomes sticky with a
 * hairline once the page scrolls. Only real in-page anchors are linked this slice (Pricing).
 */
export function LandingNav({
  theme,
  onToggleTheme,
}: {
  theme: "light" | "dark";
  onToggleTheme: () => void;
}) {
  const { t } = useTranslation();
  const [stuck, setStuck] = useState(false);
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    const onScroll = () => setStuck(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Scroll-spy: highlight the nav link for the section currently dominating the viewport.
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const ids = ["core", "ai", "security", "pricing"];
    const io = new IntersectionObserver(
      (entries) => {
        const hit = entries.filter((e) => e.isIntersecting).sort(
          (a, b) => b.intersectionRatio - a.intersectionRatio,
        )[0];
        if (hit) setActive(hit.target.id);
      },
      { rootMargin: "-45% 0px -45% 0px", threshold: 0 },
    );
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, []);

  const links: [string, string][] = [
    ["core", "landing.nav.product"],
    ["ai", "landing.nav.ai"],
    ["security", "landing.nav.security"],
    ["pricing", "landing.nav.pricing"],
  ];

  return (
    <header className={`lp-nav${stuck ? " is-stuck" : ""}`}>
      <div className="lp-wrap lp-nav__inner">
        <HashLink to="#top" className="lp-brand" aria-label={t("landing.brand")}>
          <BrandMark className="lp-brand__mark" />
          <span className="lp-brand__name">{t("landing.brand")}</span>
        </HashLink>

        <nav className="lp-nav__links" aria-label={t("landing.nav.sections")}>
          {links.map(([id, key]) => (
            <HashLink
              key={id}
              to={`#${id}`}
              className={active === id ? "is-active" : undefined}
              aria-current={active === id ? "true" : undefined}
            >
              {t(key)}
            </HashLink>
          ))}
        </nav>

        <div className="lp-nav__right">
          <LanguageSwitcher />
          <button
            type="button"
            className="lp-theme-toggle"
            onClick={onToggleTheme}
            aria-label={t(theme === "dark" ? "landing.nav.themeLight" : "landing.nav.themeDark")}
          >
            <NavIcon name={theme === "dark" ? "sun" : "moon"} />
          </button>
          <a className="lp-nav__login" href="#/login">
            {t("landing.nav.login")}
          </a>
          <a className="lp-btn lp-btn--solid lp-btn--shine" href="#/login">
            {t("landing.nav.try")}
          </a>
        </div>
      </div>
    </header>
  );
}
