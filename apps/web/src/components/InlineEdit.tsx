import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import "./InlineEdit.css";

interface InlineEditProps {
  /** The current persisted value. */
  value: string;
  /** Persist a new value. May be async (any result); the field exits edit mode once it settles. */
  onSave: (next: string) => Promise<unknown> | void;
  /** Accessible name for the trigger and the input (usually the field's label). */
  label: string;
  /** Shown (muted) when the value is empty and not editing. */
  emptyText?: string;
  placeholder?: string;
  /** Extra class on the input — e.g. "latin" for phone numbers / codes. */
  inputClassName?: string;
}

/**
 * Click-to-edit text field. Reads as plain text until you click (or focus + Enter) it, then swaps
 * to an input. Enter / ⌘Enter commit, Esc reverts, blur commits — the same calm keyboard contract
 * as the full-page forms. Editing an input is a typing target, so the global list/shortcut layers
 * stand down automatically (no key collisions). The caller's onSave owns persistence + optimism.
 */
export function InlineEdit({ value, onSave, label, emptyText = "—", placeholder, inputClassName }: InlineEditProps) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  // True when a keyboard commit/cancel ended the edit — restore focus to the trigger so Tab order
  // continues from where it was. Stays false for a blur-commit (the user moved focus on purpose).
  const restoreFocus = useRef(false);

  // Stay in sync if the persisted value changes while we're not actively editing.
  useEffect(() => {
    if (!editing) setDraft(value);
  }, [value, editing]);

  // Select-all on entering edit mode, so typing replaces and the caret is obvious.
  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    } else if (restoreFocus.current) {
      restoreFocus.current = false;
      triggerRef.current?.focus();
    }
  }, [editing]);

  async function commit() {
    if (saving) return;
    const next = draft.trim();
    if (next === value.trim()) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave(next);
    } finally {
      setSaving(false);
      setEditing(false);
    }
  }

  function cancel() {
    setDraft(value);
    setEditing(false);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      restoreFocus.current = true;
      void commit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      restoreFocus.current = true;
      cancel();
    }
  }

  if (!editing) {
    return (
      <button
        ref={triggerRef}
        type="button"
        className="inline-edit__trigger"
        onClick={() => setEditing(true)}
        aria-label={t("common.editField", { field: label })}
      >
        {value ? (
          <span>{value}</span>
        ) : (
          <span className="inline-edit__placeholder">{placeholder ?? emptyText}</span>
        )}
      </button>
    );
  }

  return (
    <input
      ref={inputRef}
      className={`inline-edit__input${inputClassName ? ` ${inputClassName}` : ""}`}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onKeyDown={onKeyDown}
      onBlur={() => void commit()}
      placeholder={placeholder}
      aria-label={label}
      disabled={saving}
    />
  );
}
