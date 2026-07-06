import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { RouteBreadcrumb } from "../app/RouteBreadcrumb";
import { usePageActions } from "../app/PageActionsContext";
import { DocumentMenu } from "./DocumentMenu";
import { Tooltip } from "./Tooltip";
import "./PageHeaderBar.css";

// react-router publishes a monotonic history index on window.history.state.idx. We read it to dim
// "back" at the start of the session; browsers never expose whether a forward entry exists, so we
// remember the furthest index seen this session (sessionStorage) and dim "forward" once the user is
// at that frontier. A heuristic — mirrors the browser buttons closely enough.
const MAX_IDX_KEY = "pageHeaderBar:maxIdx";

function historyIdx(): number {
  const idx = (window.history.state as { idx?: number } | null)?.idx;
  return typeof idx === "number" ? idx : 0;
}

function storedMax(): number {
  const raw = Number(sessionStorage.getItem(MAX_IDX_KEY));
  return Number.isFinite(raw) ? raw : 0;
}

// Chevrons drawn along the reading direction; both flip in RTL via CSS so "back" always points to
// the inline-start edge. Back points inline-start, forward inline-end (in LTR).
function BackChevron() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="m15 6-6 6 6 6" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function ForwardChevron() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="m9 6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * The sticky page header bar mounted once per route in AppShell: ‹ › history arrows, the route
 * breadcrumb, then the page's single primary action and its ⋯ menu (published via PageActionsContext).
 * Monochrome — this is CHROME. Pages publish their actions in FILE_02/03; here it renders arrows +
 * breadcrumb on every page and nothing extra until a page publishes.
 */
export function PageHeaderBar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { primary, menuItems } = usePageActions();

  const idx = historyIdx();
  const maxIdx = Math.max(storedMax(), idx);

  // Advance the remembered frontier on every navigation.
  useEffect(() => {
    sessionStorage.setItem(MAX_IDX_KEY, String(Math.max(storedMax(), historyIdx())));
  }, [location.key]);

  const canBack = idx > 0;
  const canForward = idx < maxIdx;

  return (
    <div className="pagebar">
      <div className="pagebar__inner">
        <div className="pagebar__arrows">
          <Tooltip label={t("shell.back")} placement="bottom">
            <button
              type="button"
              className="btn btn--ghost btn--icon pagebar__arrow"
              onClick={() => navigate(-1)}
              disabled={!canBack}
              aria-label={t("shell.back")}
            >
              <BackChevron />
            </button>
          </Tooltip>
          <Tooltip label={t("shell.forward")} placement="bottom">
            <button
              type="button"
              className="btn btn--ghost btn--icon pagebar__arrow"
              onClick={() => navigate(1)}
              disabled={!canForward}
              aria-label={t("shell.forward")}
            >
              <ForwardChevron />
            </button>
          </Tooltip>
        </div>
        <RouteBreadcrumb />
        <div className="pagebar__spacer" />
        {primary && <div className="pagebar__primary">{primary}</div>}
        {menuItems && menuItems.length > 0 && (
          <DocumentMenu items={menuItems} ariaLabel={t("shell.menu")} />
        )}
      </div>
    </div>
  );
}
