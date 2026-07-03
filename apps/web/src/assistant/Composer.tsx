import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { useTranslation } from "react-i18next";

import { NavIcon } from "../app/icons";

// A file the user has attached to the current turn — tracked from pick/drop/paste through upload.
export interface PendingAttachment {
  localId: string;
  name: string;
  size: number;
  contentType: string;
  status: "uploading" | "done" | "error";
  serverId?: number;
  previewUrl?: string; // object URL for image thumbnails
  error?: string; // blame-free reason when status === "error"
  file?: File; // kept so an upload error can be retried
}

interface ComposerProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  streaming: boolean;
  onStop: () => void;
  attachments: PendingAttachment[];
  onFiles: (files: FileList | File[]) => void;
  onRemoveAttachment: (localId: string) => void;
  onRetryAttachment: (localId: string) => void;
  uploading: boolean;
}

const MAX_HEIGHT = 150;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * The message composer: Enter sends, Shift+Enter adds a line. A paperclip (and paste of a
 * screenshot) attaches files, shown as chips above the input; send is held while any is still
 * uploading. While a reply streams the send button becomes a stop button.
 */
export const Composer = forwardRef<HTMLTextAreaElement, ComposerProps>(function Composer(
  { value, onChange, onSend, streaming, onStop, attachments, onFiles, onRemoveAttachment, onRetryAttachment, uploading },
  ref,
) {
  const { t } = useTranslation();
  const innerRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  useImperativeHandle(ref, () => innerRef.current as HTMLTextAreaElement, []);

  useEffect(() => {
    const el = innerRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  const canSend = !!value.trim() && !uploading;

  return (
    <div className="composer">
      {attachments.length > 0 && (
        <ul className="composer__attachments">
          {attachments.map((a) => (
            <li key={a.localId} className={`attach-chip attach-chip--${a.status}`}>
              {a.previewUrl ? (
                <img className="attach-chip__thumb" src={a.previewUrl} alt="" />
              ) : (
                <span className="attach-chip__icon" aria-hidden="true">
                  <NavIcon name="reports" />
                </span>
              )}
              <span className="attach-chip__meta">
                <span className="attach-chip__name" dir="auto">{a.name}</span>
                <span className="attach-chip__sub">
                  {a.status === "uploading"
                    ? t("assistant.uploading")
                    : a.status === "error"
                      ? a.error || t("assistant.uploadFailed")
                      : formatSize(a.size)}
                </span>
              </span>
              {a.status === "uploading" && <span className="attach-chip__spin" aria-hidden="true" />}
              {a.status === "done" && (
                <span className="attach-chip__ok" aria-hidden="true"><NavIcon name="check" /></span>
              )}
              {a.status === "error" && (
                <button
                  type="button"
                  className="attach-chip__act"
                  aria-label={t("assistant.retry")}
                  onClick={() => onRetryAttachment(a.localId)}
                >
                  <NavIcon name="rotate" />
                </button>
              )}
              <button
                type="button"
                className="attach-chip__act"
                aria-label={t("assistant.remove")}
                onClick={() => onRemoveAttachment(a.localId)}
              >
                <NavIcon name="close" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <form
        className="conversation__composer"
        onSubmit={(e) => {
          e.preventDefault();
          if (canSend) onSend();
        }}
      >
        <button
          type="button"
          className="composer__attach"
          aria-label={t("assistant.attach")}
          onClick={() => fileInput.current?.click()}
          disabled={streaming}
        >
          <NavIcon name="paperclip" />
        </button>
        <input
          ref={fileInput}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files && e.target.files.length) onFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <textarea
          ref={innerRef}
          className="conversation__input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={t("assistant.placeholder")}
          rows={1}
          dir="auto"
          onPaste={(e) => {
            const files = e.clipboardData?.files;
            if (files && files.length) {
              e.preventDefault();
              onFiles(files);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (canSend) onSend();
            }
          }}
        />
        {streaming ? (
          <button type="button" className="btn btn--ghost conversation__send" onClick={onStop}>
            {t("assistant.stop")}
          </button>
        ) : (
          <button type="submit" className="btn btn--primary conversation__send" disabled={!canSend}>
            {t("assistant.ask")}
          </button>
        )}
      </form>
    </div>
  );
});
