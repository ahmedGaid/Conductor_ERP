import { forwardRef, useEffect, useImperativeHandle, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface ComposerProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  streaming: boolean;
  onStop: () => void;
  /** Left-edge slot for future controls (session 07 mounts attachments here). */
  startSlot?: ReactNode;
}

// A textarea that grows to six rows, then scrolls.
const MAX_HEIGHT = 150;

/**
 * The message composer: Enter sends, Shift+Enter adds a line. While a reply streams the send button
 * becomes a stop button (aborting keeps the partial answer, per the server's stream behaviour). The
 * `startSlot` is left empty now — session 07 drops the attachment control there.
 */
export const Composer = forwardRef<HTMLTextAreaElement, ComposerProps>(function Composer(
  { value, onChange, onSend, streaming, onStop, startSlot },
  ref,
) {
  const { t } = useTranslation();
  const innerRef = useRef<HTMLTextAreaElement | null>(null);
  useImperativeHandle(ref, () => innerRef.current as HTMLTextAreaElement, []);

  // Auto-grow to the content, capped so a long paste scrolls instead of eating the panel.
  useEffect(() => {
    const el = innerRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  return (
    <form
      className="conversation__composer"
      onSubmit={(e) => {
        e.preventDefault();
        onSend();
      }}
    >
      {startSlot}
      <textarea
        ref={innerRef}
        className="conversation__input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t("assistant.placeholder")}
        rows={1}
        dir="auto"
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSend();
          }
        }}
      />
      {streaming ? (
        <button type="button" className="btn btn--ghost conversation__send" onClick={onStop}>
          {t("assistant.stop")}
        </button>
      ) : (
        <button type="submit" className="btn btn--primary conversation__send" disabled={!value.trim()}>
          {t("assistant.ask")}
        </button>
      )}
    </form>
  );
});
