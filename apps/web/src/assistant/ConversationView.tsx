import { useEffect, useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  answerClarify,
  cancelStream,
  chatStream,
  createConversation,
  getConversation,
  reconnectChatStream,
  resumeDetour,
  retryTurnStream,
  uploadAttachment,
  ALLOWED_ATTACHMENT_TYPES,
  MAX_ATTACHMENT_BYTES,
  type ActionProposal,
  type AskCitation,
  type AssistantClarify,
  type AssistantSuggestion,
  type AttachmentInfo,
  type ChatEvent,
  type ChatMessage,
  type ChatStep,
  type EnvelopeInfo,
  type ImportTask,
  type StopReason,
} from "../api/assistant";
import { ApiError } from "../api/client";
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
    pendingResume,
    clearPendingResume,
  } = useAssistant();

  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamSteps, setStreamSteps] = useState<ChatStep[]>([]);
  const [streamNotice, setStreamNotice] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  // T5.9: the error banner came from the conversation's persisted `last_stream_error` (worker died,
  // discovered on load/reconnect), not a live client-side failure — `retry()` needs to know which
  // recovery path applies (retry-turn vs. a plain regenerate).
  const [persistedError, setPersistedError] = useState(false);
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
    setPersistedError(false);
    const convId = conversationId;
    getConversation(convId)
      .then((d) => {
        if (!alive) return;
        setMessages(d.messages);
        // T5.9: pick up where a detached turn left off — a live worker still running (reconnect
        // to its relay) or one that died before finishing (offer retry via its own record).
        if (d.conversation.active_stream_id) {
          const checkpoint = [...d.messages].reverse()
            .find((m) => m.role === "assistant" && m.meta?.streaming === true);
          if (checkpoint) void reconnect(convId, checkpoint.id);
        } else if (d.conversation.last_stream_error) {
          setPersistedError(true);
          setStreamError(t("assistant.streamInterrupted"));
        }
      })
      .catch((err) => alive && toast.show(err instanceof Error ? err.message : String(err), "error"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // toast is stable; re-run only on id change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  // T5.9: rejoin a detached turn's live relay after a reload/network drop — patches the SAME
  // checkpoint message in place (it's already visible with its partial content from the load
  // above) instead of accumulating into a separate floating `streamText` bubble.
  async function reconnect(convId: number, checkpointMessageId: number) {
    setStreaming(true);
    setStreamNotice(null);
    const ac = new AbortController();
    abortRef.current = ac;
    let acc = messages?.find((m) => m.id === checkpointMessageId)?.content ?? "";
    let citations: AskCitation[] = [];
    let usedTool: string | null = null;
    let proposal: ActionProposal | null = null;
    let suggestion: AssistantSuggestion | null = null;
    let importTask: ImportTask | null = null;
    let envelopeInfo: EnvelopeInfo | null = null;
    let interrupted = false;
    const patch = (extra: Partial<ChatMessage["meta"]> = {}, content = acc) =>
      setMessages((m) =>
        (m ?? []).map((x) =>
          x.id === checkpointMessageId ? { ...x, content, meta: { ...x.meta, ...extra } } : x,
        ),
      );
    try {
      await reconnectChatStream(convId, (e) => {
        if (e.type === "token" && e.text) {
          acc += e.text;
          patch();
        } else if (e.type === "citations" && e.citations) {
          citations = e.citations;
        } else if (e.type === "proposal" && e.proposal) {
          proposal = e.proposal;
        } else if (e.type === "suggestion" && e.suggestion) {
          suggestion = e.suggestion;
        } else if (e.type === "import" && e.import) {
          importTask = e.import;
        } else if (e.type === "done") {
          usedTool = e.used_tool ?? null;
          if (e.budget_tokens != null && e.conversation_tokens != null) {
            envelopeInfo = {
              tokens: e.conversation_tokens, budget: e.budget_tokens, compacted: !!e.compacted,
            };
          }
        } else if (e.type === "stream-error") {
          interrupted = true;
        } else if (e.type === "error") {
          interrupted = true;
        }
      }, ac.signal);
    } catch {
      // A dropped relay (not a turn failure) — the worker may still be running; a manual reopen
      // reconciles with server truth. Leave whatever text arrived rather than erroring the turn.
    } finally {
      patch({
        streaming: undefined,
        ...(citations.length ? { citations } : {}),
        ...(usedTool ? { used_tool: usedTool } : {}),
        ...(proposal ? { proposal } : {}),
        ...(suggestion ? { suggestion } : {}),
        ...(importTask ? { import: importTask } : {}),
        ...(envelopeInfo ? { envelope: envelopeInfo } : {}),
      });
      if (interrupted) {
        setPersistedError(true);
        setStreamError(t("assistant.streamInterrupted"));
      }
      setStreaming(false);
      abortRef.current = null;
      refreshConversations();
    }
  }

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
    opts: {
      message?: string;
      regenerate?: boolean;
      attachment_ids?: number[];
      // Session 13: resume paused work after a guided detour instead of asking a new question.
      resume?: { message_id: number; resolved: { entity: string; id: string; label: string } | null };
      // T5.9: re-enqueue the last failed detached turn via the server's own record of it (there is
      // no live client-side draft to resend after a reload finds `last_stream_error`).
      retryTurn?: boolean;
      // T5.10: answer a parked clarifying question — continues the SAME agent run rather than
      // asking anything new (the answer turn is written server-side).
      clarifyAnswer?: { message_id: number; answer: string };
    },
  ) {
    setStreaming(true);
    setStreamText("");
    setStreamSteps([]);
    setStreamNotice(null);
    setStreamError(null);
    setPersistedError(false);
    const ac = new AbortController();
    abortRef.current = ac;
    let acc = "";
    let steps: ChatStep[] = [];
    let citations: AskCitation[] = [];
    let usedTool: string | null = null;
    let messageId: number | null = null;
    let proposal: ActionProposal | null = null;
    let suggestion: AssistantSuggestion | null = null;
    let clarifyCard: AssistantClarify | null = null;
    let stopReason: StopReason | null = null;
    let importTask: ImportTask | null = null;
    let envelopeInfo: EnvelopeInfo | null = null;
    let errMsg: string | null = null;
    let persistedForThisRun = false;
    // The event handling is identical across a fresh answer, a detour resume, and a T5.9 retry —
    // only the request differs (resume/retry replay server-side state; no new question needed).
    const startStream = (onEvent: (e: ChatEvent) => void) =>
      opts.clarifyAnswer
        ? answerClarify(
            { conversation_id: convId, ...opts.clarifyAnswer },
            onEvent,
            ac.signal,
          )
        : opts.resume
        ? resumeDetour(
            { conversation_id: convId, message_id: opts.resume.message_id, resolved: opts.resume.resolved },
            onEvent,
            ac.signal,
          )
        : opts.retryTurn
        ? retryTurnStream(convId, onEvent, ac.signal)
        : chatStream(
            { conversation_id: convId, context: collectContext({ detached: contextDetached }), ...opts },
            onEvent,
            ac.signal,
          );
    try {
      await startStream(
        (e) => {
          if (e.type === "plan" && e.steps) {
            // T5.2: the whole turn painted up front. Steps already finished stay as they are (a
            // replan only ever re-plans what is still ahead), so the user never watches a done
            // line revert to pending.
            const finished = steps.filter((s) => s.state === "done");
            steps = [
              ...finished,
              ...e.steps.map((s) => ({ tool: s.tool, label: s.label, state: "pending" as const })),
            ];
            setStreamSteps(steps);
          } else if (e.type === "step" && e.tool) {
            // Steps arrive strictly running-then-done; a `done` closes the last open line.
            if (e.state === "running") {
              // With a plan, the running step is one the panel already shows as pending — claim
              // that line instead of appending a duplicate. Without a plan (or for a guard step
              // the plan never listed) there is nothing to claim, so it appends as before.
              const claim = steps.findIndex((s) => s.state === "pending" && s.tool === e.tool);
              steps =
                claim === -1
                  ? [...steps, { tool: e.tool, label: e.label ?? "", state: "running" }]
                  : steps.map((s, i) =>
                      i === claim ? { ...s, label: e.label || s.label, state: "running" } : s,
                    );
            } else {
              const open = steps.map((s) => s.state).lastIndexOf("running");
              steps = steps.map((s, i) => (i === open ? { ...s, state: "done", ok: e.ok } : s));
            }
            setStreamSteps(steps);
          } else if (e.type === "retrying") {
            // T2.6: the provider dropped mid-answer — the gateway is already restarting the turn
            // on the next chain model with the partial preserved. A calm notice, never an error.
            setStreamNotice(t("assistant.streamRetrying"));
          } else if (e.type === "token" && e.text) {
            setStreamNotice(null);
            if (!acc && steps.some((s) => s.state === "pending")) {
              // The answer has started, so any step the plan listed but the run decided it didn't
              // need is never going to happen — drop those lines rather than leave them hanging.
              steps = steps.filter((s) => s.state !== "pending");
              setStreamSteps(steps);
            }
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
          } else if (e.type === "clarify" && e.clarify) {
            // T5.10: the run parked on a question — the card carries its options and the run id
            // the answer resumes.
            clarifyCard = e.clarify;
            if (e.message_id != null) messageId = e.message_id;
          } else if (e.type === "import" && e.import) {
            // A spreadsheet import card (session 14) — mapping stage, keyed to its message id.
            importTask = e.import;
            if (e.message_id != null) messageId = e.message_id;
          } else if (e.type === "done") {
            usedTool = e.used_tool ?? null;
            stopReason = e.stop_reason ?? null;
            if (e.message_id != null) messageId = e.message_id;
            if (e.budget_tokens != null && e.conversation_tokens != null) {
              envelopeInfo = {
                tokens: e.conversation_tokens, budget: e.budget_tokens, compacted: !!e.compacted,
              };
            }
          } else if (e.type === "error") {
            // T2.7: a budget block gets its own designed ar/en line, not the raw backend string
            // (which is English-only) — same "distinct code, distinct notice" precedent as T2.6's
            // streamRetrying.
            errMsg = e.code === "AI-007" ? t("assistant.budgetExceeded") : e.message ?? t("assistant.errorLine");
          } else if (e.type === "stream-error") {
            // T5.9: the worker that was running this turn went dark (reaped) while this same tab
            // was still watching — same designed line + retry affordance as a reload finding
            // `last_stream_error`, just discovered live instead of on load.
            persistedForThisRun = true;
            errMsg = t("assistant.streamInterrupted");
          }
        },
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // T5.9: another turn already claimed this conversation — calm, not an error; the existing
        // live relay (this tab's or another one's) keeps going untouched.
        toast.show(t("assistant.streamBusy"), "info");
      } else if (!ac.signal.aborted) {
        // A stop (abort) is not an error — the partial answer below still commits.
        errMsg = err instanceof Error ? err.message : String(err);
      }
    } finally {
      if (acc.trim() || proposal || suggestion || importTask || clarifyCard) {
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
            ...(clarifyCard ? { clarify: clarifyCard } : {}),
            ...(stopReason ? { stop_reason: stopReason } : {}),
            ...(importTask ? { import: importTask } : {}),
            ...(envelopeInfo ? { envelope: envelopeInfo } : {}),
          },
          created_at: new Date().toISOString(),
        };
        setMessages((m) => [...(m ?? []), asstMsg]);
        setStreamError(null);
      } else if (errMsg) {
        setStreamError(errMsg);
      }
      // T5.9: independent of whether a partial got committed above — the turn itself was
      // interrupted server-side, so retry must go through retry-turn (server truth), not a plain
      // regenerate (which would only have this tab's own, possibly-incomplete local text to redo).
      if (persistedForThisRun) setPersistedError(true);
      setStreaming(false);
      setStreamText("");
      setStreamSteps([]);
      setStreamNotice(null);
      abortRef.current = null;
      refreshConversations();
    }
  }

  // T5.10: the parked question this thread is waiting on, if any. A typed reply answers THAT
  // question — it resumes the run holding the work already gathered — rather than starting a fresh
  // turn that would ask for the same lookups again. Only the last turn counts: an older card the
  // conversation has moved past is history, not a live question.
  function parkedClarifyMessageId(): number | null {
    const last = (messages ?? []).filter((m) => m.role === "assistant").at(-1);
    if (!last || last.id <= 0) return null;
    return last.meta?.clarify?.status === "open" ? last.id : null;
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || streaming || uploading) return;
    const parked = parkedClarifyMessageId();
    if (parked != null && attachments.length === 0) {
      // The server writes the answer turn itself (so the transcript matches what the run saw) —
      // no optimistic bubble here, and the reload afterwards settles the card.
      setDraft("");
      await answerClarifyQuestion(parked, q);
      return;
    }
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

  // A guided detour returned (session 13): DetourPill selected this conversation and asked us to
  // resume. Wait until the selection has caught up and the thread has finished loading, so the
  // streamed welcome-back appends to real history instead of being overwritten by the load.
  useEffect(() => {
    if (pendingResume == null) return;
    if (conversationId !== pendingResume.conversationId || loading || messages == null) return;
    const req = pendingResume;
    clearPendingResume();
    void (async () => {
      await runStream(req.conversationId, { resume: { message_id: req.messageId, resolved: req.resolved } });
      // Reload from server truth: the resume settled (or re-opened) the original suggestion card, and
      // the optimistic append can't see that flip — a fresh fetch shows the card in its final state
      // alongside the welcome-back reply and its proposal.
      try {
        const d = await getConversation(req.conversationId);
        setMessages(d.messages);
      } catch {
        /* keep the optimistic view if the reload fails; a manual reopen will reconcile */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingResume, conversationId, loading, messages]);

  // T5.10: the user answered a parked clarify — either by tapping an option or by typing. The
  // stream continues the same run; afterwards the thread is reloaded from server truth so the
  // settled card and the server-written answer turn replace the optimistic view.
  async function answerClarifyQuestion(messageId: number, answer: string) {
    if (streaming || conversationId == null) return;
    const convId = conversationId;
    await runStream(convId, { clarifyAnswer: { message_id: messageId, answer } });
    try {
      const d = await getConversation(convId);
      setMessages(d.messages);
    } catch {
      /* keep the optimistic view if the reload fails; a manual reopen will reconcile */
    }
  }

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
    // T5.9: a persisted (server-discovered) failure has no live local draft worth resending — go
    // through retry-turn, which replays the server's own record of the last question instead.
    await runStream(conversationId, persistedError ? { retryTurn: true } : { regenerate: true });
  }

  function stop() {
    abortRef.current?.abort();
    // T5.9: detached turns keep running server-side after the local fetch is aborted — tell the
    // worker to actually stop too. Best-effort/fire-and-forget: the running stream's own `done`
    // event (stop="cancelled") is what settles the UI, not this call's response.
    if (conversationId != null) void cancelStream(conversationId).catch(() => {});
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

  // An import card advanced to (or settled at) a new stage — patch its message meta so the stage
  // persists in view. Execute also stored the same card server-side; a reload reads it back.
  function resolveImport(id: number, task: ImportTask) {
    setMessages((m) =>
      (m ?? []).map((msg) =>
        msg.id === id ? { ...msg, meta: { ...msg.meta, import: task } } : msg,
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
          streamNotice={streamNotice}
          error={streamError}
          onRegenerate={() => void regenerate()}
          onEdit={editPrompt}
          onRetry={() => void retry()}
          onFollowup={(q) => void send(q)}
          onNavigate={onNavigate}
          onResolveAction={resolveAction}
          onResolveImport={resolveImport}
          onAnswerClarify={(id, answer) => void answerClarifyQuestion(id, answer)}
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
