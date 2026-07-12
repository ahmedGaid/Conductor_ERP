import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { NavIcon } from "../app/icons";
import { getDocumentCrumb, subscribeDocumentCrumb } from "../app/DocumentCrumb";
import { Tooltip } from "../components/Tooltip";
import { collectContext } from "./context";
import { ConversationView } from "./ConversationView";
import { ThreadList } from "./ThreadList";
import { useAssistant } from "./AssistantProvider";
import "./assistant-panel.css";

// Modules with their own single-stroke icon; anything else (admin, settings…) falls back to sparkle.
const CHIP_ICONS = new Set(["sales", "purchasing", "inventory", "accounting", "crm", "pricing"]);

/**
 * The global AI panel — one component, two renderings (floating card / docked side-rail) switched
 * by `mode`. Mounted once in the app shell beside the help drawer. Chrome is monochrome; the only
 * colour lives inside the answer. Esc closes and focus returns to the trigger (copied from the help
 * drawer). The expand button leaves for the full /assistant page.
 */
export function AssistantPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { enabled, open, mode, healthMode, closePanel, setMode, contextDetached, setContextDetached,
    setConversationId } = useAssistant();
  const panelRef = useRef<HTMLElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  // The panel body shows either the active conversation or the thread history (no room for two columns).
  const [view, setView] = useState<"chat" | "threads">("chat");

  // The record the user is looking at, live: the crumb store notifies on every publish/clear, so
  // walking between records with the panel open moves the chip with the page. Detach (×) hides it
  // for this conversation — the context still travels, marked background (`detached: true`).
  const crumb = useSyncExternalStore(subscribeDocumentCrumb, getDocumentCrumb);
  const record = !contextDetached && crumb != null ? collectContext().record : null;
  const recordModule = record?.type.split(".")[0] ?? "";

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
        {record && (
          <span className="assistant-panel__context" title={t("assistant.context.viewing")}>
            <span className="assistant-panel__context-icon" aria-hidden="true">
              <NavIcon name={CHIP_ICONS.has(recordModule) ? recordModule : "sparkle"} />
            </span>
            <bdi className="assistant-panel__context-label">{record.label}</bdi>
            <Tooltip label={t("assistant.context.detach")} placement="bottom">
              <button
                type="button"
                className="assistant-panel__context-detach"
                aria-label={t("assistant.context.detach")}
                onClick={() => setContextDetached(true)}
              >
                <NavIcon name="close" />
              </button>
            </Tooltip>
          </span>
        )}
        <div className="assistant-panel__tools">
          <Tooltip label={t("assistant.threads.new")} placement="bottom">
            <button
              type="button"
              className="assistant-panel__tool"
              aria-label={t("assistant.threads.new")}
              onClick={() => {
                setConversationId(null);
                setView("chat");
              }}
            >
              <NavIcon name="plus" />
            </button>
          </Tooltip>
          <Tooltip
            label={t(view === "threads" ? "assistant.threads.backToChat" : "assistant.threads.title")}
            placement="bottom"
          >
            <button
              type="button"
              className="assistant-panel__tool"
              aria-label={t(view === "threads" ? "assistant.threads.backToChat" : "assistant.threads.title")}
              aria-pressed={view === "threads"}
              onClick={() => setView((v) => (v === "threads" ? "chat" : "threads"))}
            >
              <NavIcon name="clock" />
            </button>
          </Tooltip>
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

      {healthMode !== "full" && (
        <p className={`assistant-panel__notice assistant-panel__notice--${healthMode}`} dir="auto">
          <span className="assistant-panel__notice-icon" aria-hidden="true">
            <NavIcon name="info" />
          </span>
          {t(healthMode === "down" ? "assistant.status.down" : "assistant.status.degraded")}
        </p>
      )}

      <div className="assistant-panel__body">
        {view === "threads" ? <ThreadList onPick={() => setView("chat")} /> : <ConversationView />}
      </div>
    </aside>
  );
}
