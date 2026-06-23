/** Shared guards for the app's keyboard layers (global shortcuts + list navigation). */

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
