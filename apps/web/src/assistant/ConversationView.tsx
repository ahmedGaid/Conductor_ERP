import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import {
  chatStream,
  createConversation,
  getConversation,
  type AskCitation,
  type ChatMessage,
} from "../api/assistant";
import { NavIcon } from "../app/icons";
import { useToast } from "../app/ToastContext";
import { Bdi } from "../components/Bdi";
import { EntityLink } from "../components/EntityLink";
import { collectContext } from "./context";
import { useAssistant } from "./AssistantProvider";
import "./assistant-panel.css";

// A citation rendered inline under an assistant message — a real record the answer is built from.
function CitationLink({ c }: { c: AskCitation }) {
  if (c.type === "order") {
    return (
      <Link className="assistant-cite" to={`/sales/orders/${c.value}`}>
        <NavIcon name="sales" />
        <Bdi>{c.label}</Bdi>
      </Link>
    );
  }
  return (
    <EntityLink className="assistant-cite" type={c.type} value={c.value}>
      <NavIcon name={c.type === "customer" ? "crm" : "inventory"} />
      <Bdi>{c.label}</Bdi>
    </EntityLink>
  );
}

/**
 * The conversation surface: prior messages rendered read-only (plain text this session — the
 * markdown-lite renderer arrives in session 06) plus a composer that streams the reply through the
 * session-02 chat endpoint. Sending persists both turns server-side, so reopening the thread shows
 * the same history. With no conversation selected the first send creates one.
 */
export function ConversationView() {
  const { t } = useTranslation();
  const toast = useToast();
  const { conversationId, setConversationId, refreshConversations } = useAssistant();

  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load (or clear) the thread when the selection changes.
  useEffect(() => {
    if (conversationId == null) {
      setMessages(null);
      return;
    }
    let alive = true;
    setLoading(true);
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

  // Keep the newest message in view as the answer streams in.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, streamText]);

  async function send() {
    const text = draft.trim();
    if (!text || streaming) return;

    let convId = conversationId;
    if (convId == null) {
      try {
        const created = await createConversation();
        convId = created.id;
        setConversationId(created.id);
        setMessages([]);
        refreshConversations();
      } catch (err) {
        toast.show(err instanceof Error ? err.message : String(err), "error");
        return;
      }
    }
    if (convId == null) return; // narrow for the stream call; unreachable in practice

    // Optimistic user turn (a negative temp id never collides with a server id).
    const userMsg: ChatMessage = {
      id: -Date.now(),
      role: "user",
      content: text,
      meta: {},
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...(m ?? []), userMsg]);
    setDraft("");
    setStreaming(true);
    setStreamText("");

    const ac = new AbortController();
    abortRef.current = ac;
    let acc = "";
    let citations: AskCitation[] = [];
    try {
      await chatStream(
        { conversation_id: convId, message: text, context: collectContext() },
        (e) => {
          if (e.type === "token" && e.text) {
            acc += e.text;
            setStreamText(acc);
          } else if (e.type === "citations" && e.citations) {
            citations = e.citations;
          } else if (e.type === "error" && e.message) {
            toast.show(e.message, "error");
          }
        },
        ac.signal,
      );
      const asstMsg: ChatMessage = {
        id: -Date.now() - 1,
        role: "assistant",
        content: acc,
        meta: citations.length ? { citations } : {},
        created_at: new Date().toISOString(),
      };
      setMessages((m) => [...(m ?? []), asstMsg]);
      // Title / preview / order changed server-side — refresh the list everywhere.
      refreshConversations();
    } catch (err) {
      if (!ac.signal.aborted) {
        toast.show(err instanceof Error ? err.message : String(err), "error");
      }
    } finally {
      setStreaming(false);
      setStreamText("");
      abortRef.current = null;
    }
  }

  return (
    <div className="conversation">
      <div className="conversation__scroll" ref={scrollRef}>
        {loading ? (
          <p className="conversation__hint">{t("common.loading")}</p>
        ) : messages && messages.length === 0 && !streaming ? (
          <p className="conversation__hint">{t("assistant.threads.startHint")}</p>
        ) : (
          <ul className="conversation__messages">
            {(messages ?? []).map((m) => {
              const cites = (m.meta?.citations as AskCitation[] | undefined) ?? [];
              return (
                <li key={m.id} className={`msg msg--${m.role}`}>
                  <p className="msg__text" dir="auto">
                    {m.content}
                  </p>
                  {cites.length > 0 && (
                    <ul className="assistant-cites msg__cites">
                      {cites.map((c) => (
                        <li key={`${c.type}:${c.value}`}>
                          <CitationLink c={c} />
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
            {streaming && (
              <li className="msg msg--assistant">
                <p className="msg__text" dir="auto">
                  {streamText || <span className="conversation__hint">{t("assistant.thinking")}</span>}
                </p>
              </li>
            )}
          </ul>
        )}
      </div>

      <form
        className="conversation__composer"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <textarea
          className="conversation__input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={t("assistant.placeholder")}
          rows={2}
          dir="auto"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <button type="submit" className="btn btn--primary" disabled={streaming || !draft.trim()}>
          {streaming ? t("assistant.thinking") : t("assistant.ask")}
        </button>
      </form>
    </div>
  );
}
