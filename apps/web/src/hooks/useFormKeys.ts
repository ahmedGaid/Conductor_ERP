import { useEffect, useRef, type RefObject } from "react";
import { isModalOpen } from "../lib/keyboard";

/**
 * App-wide keyboard conventions for a single-form page:
 *   ⌘/Ctrl+Enter → submit from any field (via requestSubmit, so the form's native
 *                  validation + onSubmit run exactly as a click on the submit button would)
 *   Esc          → cancel (caller decides where to go — usually back to the list)
 *
 * Bind `formRef` to the <form>. Both stand down while a modal <dialog> owns the keyboard
 * (command palette, cheat-sheet), so typing there is never hijacked.
 */
export function useFormKeys({
  formRef,
  onCancel,
}: {
  formRef: RefObject<HTMLFormElement>;
  onCancel?: () => void;
}) {
  // Keep the latest cancel handler without re-subscribing the listener each render.
  const onCancelRef = useRef(onCancel);
  onCancelRef.current = onCancel;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (isModalOpen()) return;
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        formRef.current?.requestSubmit();
      } else if (e.key === "Escape" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const cancel = onCancelRef.current;
        if (!cancel) return;
        e.preventDefault();
        cancel();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [formRef]);
}
