import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { NavIcon } from "../app/icons";
import { Tooltip } from "../components/Tooltip";
import { AskView } from "./AskView";
import { useAssistant } from "./AssistantProvider";
import "./assistant-panel.css";

/**
 * The global AI panel — one component, two renderings (floating card / docked side-rail) switched
 * by `mode`. Mounted once in the app shell beside the help drawer. Chrome is monochrome; the only
 * colour lives inside the answer. Esc closes and focus returns to the trigger (copied from the help
 * drawer). The expand button leaves for the full /assistant page.
 */
export function AssistantPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { enabled, open, mode, closePanel, setMode } = useAssistant();
  const panelRef = useRef<HTMLElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  // Esc closes; on open, focus moves into the panel and returns to the trigger on close.
  useEffect(() => {
    if (!open) return;
    returnFocus.current = document.activeElement as HTMLElement | null;
    const raf = window.requestAnimationFrame(() => panelRef.current?.focus());
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closePanel();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.cancelAnimationFrame(raf);
      returnFocus.current?.focus?.();
    };
  }, [open, closePanel]);

  // Docked mode pushes the app content aside: flag the shell root so CSS can add the inline-end
  // margin. Cleaned up whenever we float, close, or unmount.
  useEffect(() => {
    const shell = document.querySelector<HTMLElement>(".appshell");
    if (!shell) return;
    if (open && mode === "docked") shell.setAttribute("data-assistant-docked", "");
    else shell.removeAttribute("data-assistant-docked");
    return () => shell.removeAttribute("data-assistant-docked");
  }, [open, mode]);

  if (!enabled || !open) return null;

  function expand() {
    closePanel();
    navigate("/assistant");
  }

  const docked = mode === "docked";

  return (
    <aside
      ref={panelRef}
      className={`assistant-panel assistant-panel--${mode}`}
      role="dialog"
      aria-label={t("assistant.title")}
      tabIndex={-1}
    >
      <header className="assistant-panel__head">
        <span className="assistant-panel__brand">
          <span className="assistant-panel__brand-icon" aria-hidden="true">
            <NavIcon name="sparkle" />
          </span>
          <span className="assistant-panel__title">{t("assistant.title")}</span>
        </span>
        <div className="assistant-panel__tools">
          <Tooltip label={t(docked ? "assistant.float" : "assistant.dock")} placement="bottom">
            <button
              type="button"
              className="assistant-panel__tool"
              aria-label={t(docked ? "assistant.float" : "assistant.dock")}
              onClick={() => setMode(docked ? "floating" : "docked")}
            >
              <NavIcon name="sidebar" />
            </button>
          </Tooltip>
          <Tooltip label={t("assistant.expand")} placement="bottom">
            <button
              type="button"
              className="assistant-panel__tool"
              aria-label={t("assistant.expand")}
              onClick={expand}
            >
              <NavIcon name="expand" />
            </button>
          </Tooltip>
          <Tooltip label={t("assistant.close")} placement="bottom">
            <button
              type="button"
              className="assistant-panel__tool"
              aria-label={t("assistant.close")}
              onClick={closePanel}
            >
              <NavIcon name="close" />
            </button>
          </Tooltip>
        </div>
      </header>

      <div className="assistant-panel__body">
        <AskView />
      </div>
    </aside>
  );
}
