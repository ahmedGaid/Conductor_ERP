import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { useSyncExternalStore } from "react";

import { NavIcon } from "../app/icons";
import { getDocumentCrumb, subscribeDocumentCrumb } from "../app/DocumentCrumb";
import { useToast } from "../app/ToastContext";
import { useAssistant } from "./AssistantProvider";
import { collectContext } from "./context";
import { isStale, recordMatchesDetour } from "./detour";
import "./assistant-panel.css";

/**
 * The guided-detour surface (plan session 13). While a detour is active — a suggestion sent the user
 * off to create a missing record — a slim pill sits on the page ("Waiting — creating supplier…") and
 * this component watches for the return: when the user lands on the created record's detail page we
 * bring them straight back to where they left and resume the paused work. The pill always offers the
 * manual escape hatches ("I'm done" / "Cancel") so a detour never traps the user; a stale detour
 * (>30 min) stops auto-resuming and asks first. Mounted once beside the panel in the app shell.
 */
export function DetourPill() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const { enabled, detour, clearDetour, setConversationId, openPanel, requestResume } =
    useAssistant();
  // Subscribe so a record appearing on screen (after a save) re-runs the return check live.
  const crumb = useSyncExternalStore(subscribeDocumentCrumb, getDocumentCrumb);

  const entity = detour?.expect.entity ?? "";
  const entityName = t(`assistant.suggest.entity.${entity}`, entity);

  // Hand the paused conversation back to ConversationView and ask it to resume. `resolved` is the
  // record we captured (auto-return) or null (manual "I'm done" — the server re-resolves by query).
  function finish(resolved: { entity: string; id: string; label: string } | null) {
    if (!detour) return;
    const d = detour;
    clearDetour();
    setConversationId(d.conversationId);
    openPanel();
    requestResume({ conversationId: d.conversationId, messageId: d.messageId, resolved });
    // Return the user to exactly where they left — the panel's welcome-back completes the promise.
    navigate(d.returnTo);
    toast.show(t("assistant.detour.resumed"), "info");
  }

  function cancel() {
    clearDetour();
    toast.show(t("assistant.detour.cancelled"), "info");
  }

  // Auto-return: the user landed on a detail page whose record type matches what we sent them to
  // create. Skip while still on the page we left (avoids a false match on the record already open
  // when the detour started) and while stale (then we ask, via the pill, instead of assuming).
  useEffect(() => {
    if (!detour || isStale(detour)) return;
    const ctx = collectContext();
    if (ctx.path === detour.returnTo) return;
    const record = ctx.record;
    if (!record || !recordMatchesDetour(record.type, detour.expect.entity)) return;
    finish({ entity: detour.expect.entity, id: record.id, label: record.label });
    // collectContext reads the live crumb + hash; crumb/location drive the re-check.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detour, crumb, location]);

  if (!enabled || !detour) return null;

  const stale = isStale(detour);
  return (
    <div className="detour-pill" role="status" aria-live="polite">
      <span className="detour-pill__icon" aria-hidden="true">
        <NavIcon name="sparkle" />
      </span>
      <span className="detour-pill__label" dir="auto">
        {t(stale ? "assistant.detour.stale" : "assistant.detour.waiting", { entity: entityName })}
      </span>
      <button type="button" className="detour-pill__action" onClick={() => finish(null)}>
        {t("assistant.detour.done")}
      </button>
      <button type="button" className="detour-pill__cancel" onClick={cancel}>
        {t("assistant.detour.cancel")}
      </button>
    </div>
  );
}
