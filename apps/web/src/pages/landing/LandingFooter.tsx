import { useTranslation } from "react-i18next";
import { HashLink } from "./HashLink";
import { BrandMark } from "./BrandMark";

/** Quiet, confident close: wordmark + one-line pledge + a minimal link row. */
export function LandingFooter() {
  const { t } = useTranslation();
  return (
    <footer className="lp-footer">
      <div className="lp-wrap lp-footer__inner">
        <div className="lp-footer__brand">
          <BrandMark className="lp-brand__mark" />
          <span className="lp-brand__name">{t("landing.brand")}</span>
        </div>
        <p className="lp-footer__tagline">{t("landing.footer.tagline")}</p>
        <nav className="lp-footer__links" aria-label={t("landing.footer.linksLabel")}>
          <HashLink to="#pricing">{t("landing.nav.pricing")}</HashLink>
          <a href="#/login">{t("landing.nav.login")}</a>
        </nav>
        <p className="lp-footer__note">{t("landing.footer.note")}</p>
      </div>
    </footer>
  );
}
