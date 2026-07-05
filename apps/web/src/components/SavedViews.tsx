import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../app/icons";
import { Popover } from "./Popover";
import { Tooltip } from "./Tooltip";
import type { SavedViewsApi } from "../hooks/useSavedViews";
import type { SavedView } from "../api/savedViews";
import "./SavedViews.css";

/**
 * The saved-views control: a quiet dropdown at the start of the filter bar. It names the active
 * preset (or "All"), lists the user's views for this list, and — when the current filters aren't
 * already saved — offers "Save view". Rename / delete / set-default live as row actions. Holds no
 * data of its own; everything flows through {@link SavedViewsApi} (the `useSavedViews` hook).
 */
export function SavedViews({ api }: { api: SavedViewsApi }) {
  const { t } = useTranslation();
  const { views, activeView, canSave, applyView, saveView, renameView, deleteView, setDefaultView } = api;

  const [menuOpen, setMenuOpen] = useState(false);
  // A single inline text editor, shared by "save new" and "rename".
  const [editing, setEditing] = useState<{ mode: "save" } | { mode: "rename"; view: SavedView } | null>(null);
  const [name, setName] = useState("");

  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const saveRef = useRef<HTMLButtonElement | null>(null);

  function openEditor(next: { mode: "save" } | { mode: "rename"; view: SavedView }) {
    setName(next.mode === "rename" ? next.view.name : "");
    setEditing(next);
    setMenuOpen(false);
  }

  function submitEditor(e: FormEvent) {
    e.preventDefault();
    const value = name.trim();
    if (!value) return;
    if (editing?.mode === "save") saveView(value);
    else if (editing?.mode === "rename") renameView(editing.view, value);
    setEditing(null);
    setName("");
  }

  const editorAnchor = editing?.mode === "save" ? saveRef : triggerRef;

  return (
    <div className="savedviews">
      <button
        ref={triggerRef}
        type="button"
        className="btn btn--ghost btn--sm savedviews__trigger"
        aria-haspopup="dialog"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((o) => !o)}
      >
        <span className="savedviews__name">{activeView ? activeView.name : t("views.all")}</span>
        <NavIcon name="expand" />
      </button>

      {canSave && (
        <button
          ref={saveRef}
          type="button"
          className="btn btn--ghost btn--sm savedviews__save"
          onClick={() => openEditor({ mode: "save" })}
        >
          {t("views.save")}
        </button>
      )}

      {/* The view list */}
      <Popover open={menuOpen} onClose={() => setMenuOpen(false)} anchorRef={triggerRef} ariaLabel={t("views.label")}>
        <div className="popover__menu">
          <button
            type="button"
            className={activeView ? "popover__item" : "popover__item popover__item--on"}
            onClick={() => {
              applyView(null);
              setMenuOpen(false);
            }}
          >
            {t("views.all")}
            {!activeView && <span className="popover__check" aria-hidden="true"><NavIcon name="check" /></span>}
          </button>

          {views.length === 0 && <p className="popover__empty">{t("views.empty")}</p>}

          {views.map((view) => {
            const isActive = activeView?.id === view.id;
            return (
              <div key={view.id} className="savedviews__row">
                <button
                  type="button"
                  className={isActive ? "savedviews__pick savedviews__pick--on" : "savedviews__pick"}
                  onClick={() => {
                    applyView(view);
                    setMenuOpen(false);
                  }}
                >
                  <span className="savedviews__pick-name">{view.name}</span>
                  {isActive && <span className="savedviews__check" aria-hidden="true"><NavIcon name="check" /></span>}
                </button>
                <div className="savedviews__actions">
                  <Tooltip label={t("views.setDefault")} placement="top">
                    <button
                      type="button"
                      className={view.is_default ? "savedviews__action savedviews__action--on" : "savedviews__action"}
                      aria-label={t("views.setDefault")}
                      aria-pressed={view.is_default}
                      onClick={() => setDefaultView(view)}
                    >
                      <NavIcon name="star" />
                    </button>
                  </Tooltip>
                  <Tooltip label={t("views.rename")} placement="top">
                    <button
                      type="button"
                      className="savedviews__action"
                      aria-label={t("views.rename")}
                      onClick={() => openEditor({ mode: "rename", view })}
                    >
                      <NavIcon name="edit" />
                    </button>
                  </Tooltip>
                  <Tooltip label={t("views.delete")} placement="top">
                    <button
                      type="button"
                      className="savedviews__action"
                      aria-label={t("views.delete")}
                      onClick={() => deleteView(view)}
                    >
                      <NavIcon name="trash" />
                    </button>
                  </Tooltip>
                </div>
              </div>
            );
          })}
        </div>
      </Popover>

      {/* Inline name editor (shared by save + rename) */}
      <Popover open={editing !== null} onClose={() => setEditing(null)} anchorRef={editorAnchor} ariaLabel={t("views.save")}>
        <form className="popover__editor savedviews__editor" onSubmit={submitEditor}>
          <input
            type="text"
            autoFocus
            maxLength={60}
            placeholder={t("views.namePlaceholder")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label={t("views.namePlaceholder")}
          />
          <button type="submit" className="btn btn--primary btn--sm" disabled={!name.trim()}>
            {t("views.create")}
          </button>
        </form>
      </Popover>
    </div>
  );
}
