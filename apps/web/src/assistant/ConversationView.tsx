import { useEffect, useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  chatStream,
  createConversation,
  getConversation,
  uploadAttachment,
  ALLOWED_ATTACHMENT_TYPES,
  MAX_ATTACHMENT_BYTES,
  type ActionProposal,
  type AskCitation,
  type AssistantSuggestion,
  type AttachmentInfo,
  type ChatMessage,
  type ChatStep,
} from "../api/assistant";
import { NavIcon } from "../app/icons";
import { useToast } from "../app/ToastContext";
import { collectContext } from "./context";
import { useAssistant } from "./AssistantProvider";
import { Composer, type PendingAttachment } from "./Composer";
import { MessageList } from "./MessageList";
import { suggestionKeys } from "./suggestions";
import "./assistant-panel.css";

/**
 * The conversation surface: a streaming transcript (MessageList) above a composer. Sending persists
 * both turns server-side, so reopening the thread shows the same history; with no conversation
 * selected the first send creates one. This one component powers both the docked/floating panel and
 * the fullscreen page — they share the provider's list + selection, so they never disagree.
 */
export function ConversationView() {
  const { t } = useTranslation();
  const toast = useToast();
  const {
    conversationId,
    setConversationId,
    refreshConversations,
    open,
    mode,
    closePanel,
    pendingMessage,
    clearPendingMessage,
    contextDetached,
  } = useAssistant();

  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamSteps, setStreamSteps] = useState<ChatStep[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [dragging, setDragging] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const dragDepth = useRef(0);

  // Load (or clear) the thread when the selection changes.
  useEffect(() => {
    if (conversationId == null) {
      setMessages(null);
      setStreamError(null);
      return;
    }
    let alive = true;
    setLoading(true);
    setStreamError(null);
    getConversation(conversationId)
      .then((d) => alive && setMessages(d.messages))
      .catch((err) => alive && toast.show(err instanceof Error ? err.message : String(err), "error"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // toast is stable; re-run only on id change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  // Cancel any in-flight stream on unmount.
  useEffect(() => () => abortRef.current?.abort(), []);

  // --- attachments -----------------------------------------------------------------------------
  const uploading = attachments.some((a) => a.status === "uploading");

  function addFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const localId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const previewUrl = file.type.startsWith("image/") ? URL.createObjectURL(file) : undefined;
      const base: PendingAttachment = {
        localId, name: file.name, size: file.size, contentType: file.type,
        status: "uploading", previewUrl, file,
      };
      const tooBig = file.size > MAX_ATTACHMENT_BYTES;
      const badType = !ALLOWED_ATTACHMENT_TYPES.has(file.type);
      if (tooBig || badType) {
        setAttachments((a) => [
          ...a,
          { ...base, status: "error", error: t(tooBig ? "assistant.fileTooLarge" : "assistant.fileType") },
        ]);
        continue;
      }
      setAttachments((a) => [...a, base]);
      void uploadOne(localId, file);
    }
  }

  async function uploadOne(localId: string, file: File) {
    try {
      const info = await uploadAttachment(file);
      setAttachments((a) =>
        a.map((x) => (x.localId === localId ? { ...x, status: "done", serverId: info.id } : x)),
      );
    } catch (err) {
      const reason = err instanceof Error ? err.message : t("assistant.uploadFailed");
      setAttachments((a) =>
        a.map((x) => (x.localId === localId ? { ...x, status: "error", error: reason } : x)),
      );
    }
  }

  function removeAttachment(localId: string) {
    setAttachments((a) => {
      const found = a.find((x) => x.localId === localId);
      if (found?.previewUrl) URL.revokeObjectURL(found.previewUrl);
      return a.filter((x) => x.localId !== localId);
    });
  }

  function retryAttachment(localId: string) {
    const found = attachments.find((x) => x.localId === localId);
    if (!found?.file) return;
    setAttachments((a) =>
      a.map((x) => (x.localId === localId ? { ...x, status: "uploading", error: undefined } : x)),
    );
    void uploadOne(localId, found.file);
  }

  function clearAttachments() {
    attachments.forEach((a) => a.previewUrl && URL.revokeObjectURL(a.previewUrl));
    setAttachments([]);
  }

  // --- streaming -------------------------------------------------------------------------------
  async function ensureConversation(): Promise<number | null> {
    if (conversationId != null) return conversationId;
    try {
      const created = await createConversation();
      setConversationId(created.id);
      setMessages([]);
      refreshConversations();
      return created.id;
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
      return null;
    }
  }

  async function runStream(
    convId: number,
    opts: { message?: string; regenerate?: boolean; attachment_ids?: number[] },
  ) {
    setStreaming(true);
    setStreamText("");
    setStreamSteps([]);
    setStreamError(null);
    const ac = new AbortController();
    abortRef.current = ac;
    let acc = "";
    let steps: ChatStep[] = [];
    let citations: AskCitation[] = [];
    let usedTool: string | null = null;
    let messageId: number | null = null;
    let proposal: ActionProposal | null = null;
    let suggestion: AssistantSuggestion | null = null;
    let errMsg: string | null = null;
    try {
      await chatStream(
        { conversation_id: convId, context: collectContext({ detached: contextDetached }), ...opts },
        (e) => {
          if (e.type === "step" && e.tool) {
            // Steps arrive strictly running-then-done; a `done` closes the last open line.
            if (e.state === "running") {
              steps = [...steps, { tool: e.tool, label: e.label ?? "", state: "running" }];
            } else {
              steps = steps.map((s, i) =>
                i === steps.length - 1 ? { ...s, state: "done", ok: e.ok } : s,
              );
            }
            setStreamSteps(steps);
          } else if (e.type === "token" && e.text) {
            acc += e.text;
            setStreamText(acc);
          } else if (e.type === "citations" && e.citations) {
            citations = e.citations;
          } else if (e.type === "proposal" && e.proposal) {
            // A prepared write awaiting confirm — carries the real server message id it's keyed to.
            proposal = e.proposal;
            if (e.message_id != null) messageId = e.message_id;
          } else if (e.type === "suggestion" && e.suggestion) {
            // A blocker turned actionable (session 12) — rides the message meta like a proposal.
            suggestion = e.suggestion;
            if (e.message_id != null) messageId = e.message_id;
          } else if (e.type === "done") {
            usedTool = e.used_tool ?? null;
            if (e.message_id != null) messageId = e.message_id;
          } else if (e.type === "error") {
            errMsg = e.message ?? t("assistant.errorLine");
          }
        },
        ac.signal,
      );
    } catch (err) {
      // A stop (abort) is not an error — the partial answer below still commits.
      if (!ac.signal.aborted) errMsg = err instanceof Error ? err.message : String(err);
    } finally {
      if (acc.trim() || proposal || suggestion) {
        const asstMsg: ChatMessage = {
          // Use the real server id when we got one, so a proposal card can execute against it.
          id: messageId ?? -Date.now() - 1,
          role: "assistant",
          content: acc,
          meta: {
            ...(citations.length ? { citations } : {}),
            ...(usedTool ? { used_tool: usedTool } : {}),
            ...(steps.length ? { steps } : {}),
            ...(proposal ? { proposal } : {}),
            ...(suggestion ? { suggestion } : {}),
          },
          created_at: new Date().toISOString(),
        };
        setMessages((m) => [...(m ?? []), asstMsg]);
        setStreamError(null);
      } else if (errMsg) {
        setStreamError(errMsg);
      }
      setStreaming(false);
      setStreamText("");
      setStreamSteps([]);
      abortRef.current = null;
      refreshConversations();
    }
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || streaming || uploading) return;
    const ready = attachments.filter((a) => a.status === "done" && a.serverId != null);
    const convId = await ensureConversation();
    if (convId == null) return;
    const chips: AttachmentInfo[] = ready.map((a) => ({
      id: a.serverId as number, name: a.name, content_type: a.contentType, size: a.size,
    }));
    const userMsg: ChatMessage = {
      id: -Date.now(),
      role: "user",
      content: q,
      meta: chips.length ? { attachments: chips } : {},
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...(m ?? []), userMsg]);
    setDraft("");
    clearAttachments();
    const ids = ready.map((a) => a.serverId as number);
    await runStream(convId, { message: q, ...(ids.length ? { attachment_ids: ids } : {}) });
  }

  // A question handed off from elsewhere (the ⌘K fallthrough row) — send it once, like a normal
  // typed message, then clear it so it isn't resent on the next render.
  useEffect(() => {
    if (pendingMessage == null) return;
    clearPendingMessage();
    void send(pendingMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingMessage]);

  async function regenerate() {
    if (streaming || conversationId == null) return;
    setMessages((m) => {
      if (!m) return m;
      const idx = m.map((x) => x.role).lastIndexOf("assistant");
      return idx === -1 ? m : m.slice(0, idx);
    });
    await runStream(conversationId, { regenerate: true });
  }

  async function retry() {
    if (streaming || conversationId == null) return;
    await runStream(conversationId, { regenerate: true });
  }

  function stop() {
    abortRef.current?.abort();
  }

  function editPrompt(text: string) {
    setDraft(text);
    const el = composerRef.current;
    if (!el) return;
    el.focus();
    requestAnimationFrame(() => el.setSelectionRange(text.length, text.length));
  }

  function onNavigate() {
    if (open && mode === "floating") closePanel();
  }

  // A proposal card was confirmed/dismissed — patch its message meta so the settled state persists
  // in view (the server already stored the same status; a reload reads it back identically).
  function resolveAction(id: number, proposal: ActionProposal) {
    setMessages((m) =>
      (m ?? []).map((msg) =>
        msg.id === id ? { ...msg, meta: { ...msg.meta, proposal } } : msg,
      ),
    );
  }

  // --- drag-and-drop (whole surface) -----------------------------------------------------------
  const hasFiles = (e: DragEvent) => e.dataTransfer?.types?.includes("Files");

  const showEmpty =
    !loading && !streaming && !streamError && (messages == null || messages.length === 0);

  return (
    <div
      className="conversation"
      onDragEnter={(e) => {
        if (!hasFiles(e)) return;
        e.preventDefault();
        dragDepth.current += 1;
        setDragging(true);
      }}
      onDragOver={(e) => {
        if (hasFiles(e)) e.preventDefault();
      }}
      onDragLeave={() => {
        dragDepth.current = Math.max(0, dragDepth.current - 1);
        if (dragDepth.current === 0) setDragging(false);
      }}
      onDrop={(e) => {
        if (e.dataTransfer?.files?.length) {
          e.preventDefault();
          addFiles(e.dataTransfer.files);
        }
        dragDepth.current = 0;
        setDragging(false);
      }}
    >
      {dragging && (
        <div className="conversation__drop" aria-hidden="true">
          <span className="conversation__drop-hint">
            <NavIcon name="paperclip" />
            {t("assistant.dropHint")}
          </span>
        </div>
      )}

      {loading ? (
        <div className="conversation__scroll">
          <p className="conversation__hint">{t("common.loading")}</p>
        </div>
      ) : showEmpty ? (
        <div className="conversation__scroll">
          <div className="conversation__empty">
            <span className="conversation__empty-icon" aria-hidden="true">
              <NavIcon name="sparkle" />
            </span>
            <p className="conversation__empty-lead" dir="auto">{t("assistant.subtitle")}</p>
            <p className="conversation__empty-hint">{t("assistant.tryLabel")}</p>
            <ul className="msg-followups__list">
              {(() => {
                // Module-aware chips (session 11): what the user can ask *here* — record questions
                // on a detail page (unless detached), the module's reports on its lists, the
                // original four everywhere else. Recomputed per render, so navigation refreshes it.
                const ctx = collectContext();
                return suggestionKeys(ctx.module, ctx.record != null && !contextDetached);
              })().map((k) => {
                const q = t(k);
                return (
                  <li key={k}>
                    <button type="button" className="msg-followups__chip" onClick={() => void send(q)}>
                      {q}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      ) : (
        <MessageList
          messages={messages ?? []}
          streaming={streaming}
          streamText={streamText}
          streamSteps={streamSteps}
          error={streamError}
          onRegenerate={() => void regenerate()}
          onEdit={editPrompt}
          onRetry={() => void retry()}
          onFollowup={(q) => void send(q)}
          onNavigate={onNavigate}
          onResolveAction={resolveAction}
        />
      )}

      <Composer
        ref={composerRef}
        value={draft}
        onChange={setDraft}
        onSend={() => void send(draft)}
        streaming={streaming}
        onStop={stop}
        attachments={attachments}
        onFiles={addFiles}
        onRemoveAttachment={removeAttachment}
        onRetryAttachment={retryAttachment}
        uploading={uploading}
      />
    </div>
  );
}
