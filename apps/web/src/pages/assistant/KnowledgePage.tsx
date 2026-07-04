import { Fragment, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  ALLOWED_KNOWLEDGE_TYPES,
  MAX_ATTACHMENT_BYTES,
  deleteKnowledge,
  listKnowledge,
  uploadKnowledge,
  type KnowledgeDoc,
} from "../../api/assistant";
import { NavIcon } from "../../app/icons";
import { useToast } from "../../app/ToastContext";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { useAsync } from "../../hooks/useAsync";
import { runOptimistic } from "../../lib/optimistic";
import "./knowledge.css";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Admin-only knowledge-base management: upload documents the assistant's search_documents tool can
// find and quote (session 04), watch each land on "ready" or "failed", and delete what's no longer
// current. Ingestion is synchronous server-side, so a fresh row starts "processing" and the list
// polls in place via reload after the upload call resolves.
export function KnowledgePage() {
  const { t } = useTranslation();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);

  const { data, loading, error, reload, mutate } = useAsync(listKnowledge, [], "assistant:knowledge");
  const docs = data ?? [];

  const [title, setTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<KnowledgeDoc | null>(null);

  function pickFile() {
    fileRef.current?.click();
  }

  async function onFileChosen(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_ATTACHMENT_BYTES) {
      toast.show(t("knowledge.fileTooLarge"), "error");
      return;
    }
    if (!ALLOWED_KNOWLEDGE_TYPES.has(file.type)) {
      toast.show(t("knowledge.fileType"), "error");
      return;
    }
    const docTitle = title.trim();
    const tempId = -Date.now();
    const placeholder: KnowledgeDoc = {
      id: tempId,
      title: docTitle || file.name,
      filename: file.name,
      status: "processing",
      error_text: "",
      chunk_count: 0,
      size: file.size,
      updated_at: new Date().toISOString(),
    };
    setUploading(true);
    setTitle("");
    await runOptimistic<KnowledgeDoc[], KnowledgeDoc>({
      current: docs,
      mutate,
      optimistic: (rows) => [placeholder, ...rows],
      request: () => uploadKnowledge(file, docTitle),
      settle: (predicted, created) => predicted.map((r) => (r.id === tempId ? created : r)),
      toast,
      errorMessage: () => t("knowledge.uploadFailed"),
    });
    setUploading(false);
  }

  function confirmDelete() {
    const d = pendingDelete;
    setPendingDelete(null);
    if (!d) return;
    void runOptimistic<KnowledgeDoc[], void>({
      current: docs,
      mutate,
      optimistic: (rows) => rows.filter((r) => r.id !== d.id),
      request: () => deleteKnowledge(d.id),
      toast,
      errorMessage: () => t("knowledge.deleteFailed"),
    });
  }

  return (
    <section className="page-enter">
      <header className="module-head">
        <h1 className="module-head__title">{t("knowledge.title")}</h1>
        <p className="module-head__desc">{t("knowledge.subtitle")}</p>
      </header>

      <div className="card knowledge-upload">
        <input
          className="knowledge-upload__title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t("knowledge.docTitlePlaceholder")}
          aria-label={t("knowledge.docTitle")}
        />
        <input
          ref={fileRef}
          type="file"
          className="knowledge-upload__input"
          accept={[...ALLOWED_KNOWLEDGE_TYPES].join(",")}
          onChange={(e) => {
            void onFileChosen(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        <button type="button" className="btn btn--primary" onClick={pickFile} disabled={uploading}>
          <NavIcon name="paperclip" />
          {t("knowledge.upload")}
        </button>
      </div>

      {loading && <ListSkeleton rows={2} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && docs.length === 0 && (
        <EmptyState title={t("knowledge.empty.title")} hint={t("knowledge.empty.body")} />
      )}

      {docs.length > 0 && (
        <div className="card knowledge-table-wrap">
          <table className="knowledge-table">
            <thead>
              <tr>
                <th>{t("knowledge.docTitle")}</th>
                <th>{t("knowledge.filename")}</th>
                <th>{t("knowledge.size")}</th>
                <th>{t("knowledge.statusCol")}</th>
                <th>{t("knowledge.chunks")}</th>
                <th>{t("knowledge.updated")}</th>
                <th aria-hidden="true"></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <Fragment key={d.id}>
                  <tr className="knowledge-row">
                    <td>{d.title}</td>
                    <td className="latin muted">{d.filename}</td>
                    <td className="latin muted">{formatSize(d.size)}</td>
                    <td>
                      <span className={`kpill kpill--${d.status}`} data-status={d.status}>
                        {t(`knowledge.status.${d.status}`)}
                      </span>
                    </td>
                    <td className="latin muted">{d.chunk_count}</td>
                    <td className="latin muted">{d.updated_at.slice(0, 10)}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--sm knowledge-row__delete"
                        aria-label={t("knowledge.delete")}
                        onClick={() => setPendingDelete(d)}
                      >
                        <NavIcon name="trash" />
                      </button>
                    </td>
                  </tr>
                  {d.status === "failed" && d.error_text && (
                    <tr className="knowledge-row__error-row">
                      <td colSpan={7} className="knowledge-row__error">
                        {d.error_text}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={pendingDelete != null}
        title={t("knowledge.delete")}
        body={t("knowledge.deleteConfirm")}
        confirmLabel={t("knowledge.delete")}
        danger
        onConfirm={confirmDelete}
        onClose={() => setPendingDelete(null)}
      />
    </section>
  );
}
