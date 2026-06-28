import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { NavIcon } from "../app/icons";
import "./moduleHeader.css";

/**
 * ModuleHeader — calm, monochrome wayfinding for a transaction detail page.
 *
 * Identity comes from icon + place, never colour (Linear/Stripe/GitHub pattern):
 *   1. a breadcrumb — [module glyph] Module › Section — the module name links back,
 *   2. the same single-stroke module glyph beside the document title.
 * The chrome stays monochrome; the only colour on the page is the status badge passed
 * in via `status`, where colour actually means something. The glyph reuses our own
 * NavIcon set (the exact icon the sidebar shows for that module), so the header echoes
 * the active nav item — you recognise the module by shape, and it survives grayscale.
 */
export interface ModuleHeaderProps {
  /** Module key — drives the glyph + the translated module name (nav.*). */
  module: string;
  /** Where the breadcrumb's module crumb links (e.g. "/sales"). */
  moduleTo: string;
  /** Section label for the breadcrumb tail (e.g. t("sales.tabs.orders")). */
  section: string;
  /** The document number/title (rendered in the Latin face). */
  title: string;
  /** The page's own status badge — the one place colour is allowed. */
  status?: ReactNode;
  /** Optional sub-line under the title (party · warehouse · date, etc.). */
  subtitle?: ReactNode;
}

export function ModuleHeader({ module, moduleTo, section, title, status, subtitle }: ModuleHeaderProps) {
  const { t } = useTranslation();
  const moduleName = t(`nav.${module}`);

  return (
    <div className="modhead">
      <nav className="modhead__crumb" aria-label={t("common.breadcrumb")}>
        <Link to={moduleTo} className="modhead__crumb-module">
          <span className="modhead__crumb-icon">
            <NavIcon name={module} />
          </span>
          <span>{moduleName}</span>
        </Link>
        <svg className="modhead__chev" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="m9 6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="modhead__crumb-current">{section}</span>
      </nav>

      <div className="modhead__row">
        <span
          className="modhead__bar"
          aria-hidden="true"
          style={{ background: `var(--module-${module}-bar, var(--color-border-strong))` }}
        />
        <h2 className="latin modhead__title">{title}</h2>
        {status != null && <span className="modhead__status">{status}</span>}
      </div>

      {subtitle != null && <p className="muted modhead__subtitle">{subtitle}</p>}
    </div>
  );
}
