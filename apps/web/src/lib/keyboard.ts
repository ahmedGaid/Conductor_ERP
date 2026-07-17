/** Shared guards for the app's keyboard layers (global shortcuts + list navigation). */

/** True on macOS — the ⌘ glyph only reads correctly there; everywhere else shows "Ctrl". */
export function isMac(): boolean {
  if (typeof navigator === "undefined") return false;
  return /Mac|iPod|iPhone|iPad/.test(navigator.userAgent);
}

/** The platform's modifier key label for shortcut hints: "⌘" on macOS, "Ctrl" elsewhere. */
export function modKey(): string {
  return isMac() ? "⌘" : "Ctrl";
}

/**
 * A modifier+key combo for a single kbd chip, in each platform's own convention:
 * "⌘K" on macOS (glyph glued to the key, no separator), "Ctrl+K" elsewhere.
 */
export function modKeyCombo(key: string): string {
  return isMac() ? `⌘${key}` : `Ctrl+${key}`;
}

/** True when the event target is an editable field, so bare single-key shortcuts must stand down. */
export function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

/** True while a modal <dialog> owns the keyboard (command palette, cheat-sheet, etc.). */
export function isModalOpen(): boolean {
  return document.querySelector("dialog[open]") !== null;
}
