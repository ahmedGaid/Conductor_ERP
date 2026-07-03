import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  chatStream,
  createConversation,
  getConversation,
  type AskCitation,
  type ChatMessage,
} from "../api/assistant";
import { NavIcon } from "../app/icons";
import { useToast } from "../app/ToastContext";
import { collectContext } from "./context";
import { useAssistant } from "./AssistantProvider";
import { Composer } from "./Composer";
import { MessageList } from "./MessageList";
import { firstRunSuggestions } from "./suggestions";
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
  const { conversationId, setConversationId, refreshConversations, open, mode, closePanel } =
    useAssistant();

  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamError, setStreamError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);

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

  // The streaming half — shared by a fresh send, a retry and a regenerate. `opts` carries either a
  // new `message` or the `regenerate` flag (re-answer the last question in place).
  async function runStream(convId: number, opts: { message?: string; regenerate?: boolean }) {
    setStreaming(true);
    setStreamText("");
    setStreamError(null);
    const ac = new AbortController();
    abortRef.current = ac;
    let acc = "";
    let citations: AskCitation[] = [];
    let usedTool: string | null = null;
    let errMsg: string | null = null;
    try {
      await chatStream(
        { conversation_id: convId, context: collectContext(), ...opts },
        (e) => {
          if (e.type === "token" && e.text) {
            acc += e.text;
            setStreamText(acc);
          } else if (e.type === "citations" && e.citations) {
            citations = e.citations;
          } else if (e.type === "done") {
            usedTool = e.used_tool ?? null;
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
      if (acc.trim()) {
        const asstMsg: ChatMessage = {
          id: -Date.now() - 1,
          role: "assistant",
          content: acc,
          meta: {
            ...(citations.length ? { citations } : {}),
            ...(usedTool ? { used_tool: usedTool } : {}),
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
      abortRef.current = null;
      // Title / preview / order changed server-side — refresh the list everywhere.
      refreshConversations();
    }
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || streaming) return;
    const convId = await ensureConversation();
    if (convId == null) return;
    // Optimistic user turn (a negative temp id never collides with a server id).
    const userMsg: ChatMessage = {
      id: -Date.now(),
      role: "user",
      content: q,
      meta: {},
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...(m ?? []), userMsg]);
    setDraft("");
    await runStream(convId, { message: q });
  }

  async function regenerate() {
    if (streaming || conversationId == null) return;
    // Drop the last answer locally; the server drops it too before re-answering.
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

  // Internal citations/links navigate — a floating panel gets out of the way; docked/page stay.
  function onNavigate() {
    if (open && mode === "floating") closePanel();
  }

  const showEmpty =
    !loading && !streaming && !streamError && (messages == null || messages.length === 0);

  return (
    <div className="conversation">
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
              {firstRunSuggestions().map((k) => {
                const q = t(`assistant.suggestions.${k}`);
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
          error={streamError}
          onRegenerate={() => void regenerate()}
          onEdit={editPrompt}
          onRetry={() => void retry()}
          onFollowup={(q) => void send(q)}
          onNavigate={onNavigate}
        />
      )}

      <Composer
        ref={composerRef}
        value={draft}
        onChange={setDraft}
        onSend={() => void send(draft)}
        streaming={streaming}
        onStop={stop}
      />
    </div>
  );
}
