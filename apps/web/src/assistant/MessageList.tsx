import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { AskCitation, AttachmentInfo, ChatMessage, ChatStep } from "../api/assistant";
import { NavIcon } from "../app/icons";
import { useToast } from "../app/ToastContext";
import { Bdi } from "../components/Bdi";
import { EntityLink } from "../components/EntityLink";
import { Tooltip } from "../components/Tooltip";
import { Markdown } from "./Markdown";
import { followupsFor, type SuggestionKey } from "./suggestions";

// A citation under an assistant message — a real record the answer is built from, click-through so
// every number is verifiable. Internal navigation closes a floating panel via `onNavigate`.
// Citation type → (EntityLink type, the nav icon of its home module). "order" is handled apart
// because a sales-order citation carries the record id (a direct /sales/orders/:id link), while
// the rest resolve through EntityLink by their business code/number.
const CITE_ENTITY: Record<
  Exclude<AskCitation["type"], "order">,
  { type: "customer" | "item" | "supplier" | "purchaseOrder" | "journal"; icon: string }
> = {
  customer: { type: "customer", icon: "crm" },
  item: { type: "item", icon: "inventory" },
  supplier: { type: "supplier", icon: "purchasing" },
  purchaseOrder: { type: "purchaseOrder", icon: "purchasing" },
  journal: { type: "journal", icon: "accounting" },
};

function CitationLink({ c, onNavigate }: { c: AskCitation; onNavigate?: () => void }) {
  if (c.type === "order") {
    return (
      <Link className="assistant-cite" to={`/sales/orders/${c.value}`} onClick={onNavigate}>
        <NavIcon name="sales" />
        <Bdi>{c.label}</Bdi>
      </Link>
    );
  }
  const e = CITE_ENTITY[c.type];
  return (
    <EntityLink className="assistant-cite" type={e.type} value={c.value} onClick={onNavigate}>
      <NavIcon name={e.icon} />
      <Bdi>{c.label}</Bdi>
    </EntityLink>
  );
}

// The agent's reasoning surface (session 09). While streaming, each tool call renders as a quiet
// line — a clock while running, a check when done (a cross if the tool refused) — no spinner
// carnival. After the answer lands it collapses to one "Checked N sources" line that expands on
// click: calm by default, the full trail one tap away.
function StepIcon({ step }: { step: ChatStep }) {
  if (step.state === "running") return <NavIcon name="clock" />;
  return <NavIcon name={step.ok === false ? "close" : "check"} />;
}

function StepStack({ steps }: { steps: ChatStep[] }) {
  const { t } = useTranslation();
  return (
    <ul className="msg-steps" aria-label={t("assistant.stepsLabel")}>
      {steps.map((s, i) => (
        <li key={i} className={`msg-steps__item msg-steps__item--${s.state ?? "done"}`}>
          <span className="msg-steps__icon" aria-hidden="true">
            <StepIcon step={s} />
          </span>
          <span className="msg-steps__label" dir="auto">{s.label ?? s.why ?? s.tool}</span>
        </li>
      ))}
    </ul>
  );
}

function StepsSummary({ steps }: { steps: ChatStep[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <div className="msg-steps-summary">
      <button
        type="button"
        className="msg-steps-summary__toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <NavIcon name="check" />
        {t("assistant.stepsSummary", { count: steps.length })}
      </button>
      {open && <StepStack steps={steps} />}
    </div>
  );
}

interface MessageListProps {
  messages: ChatMessage[];
  streaming: boolean;
  streamText: string;
  streamSteps: ChatStep[];
  error: string | null;
  onRegenerate: () => void;
  onEdit: (text: string) => void;
  onRetry: () => void;
  onFollowup: (question: string) => void;
  onNavigate?: () => void;
}

/**
 * The conversation transcript: prior turns rendered through the in-house Markdown, the in-flight
 * streaming bubble, and the hover actions (copy / regenerate / edit prompt). Auto-scroll pins to the
 * bottom only while the reader is already there — reading history mid-stream is never yanked away;
 * a quiet "new reply" chip offers the jump instead.
 */
export function MessageList({
  messages,
  streaming,
  streamText,
  streamSteps,
  error,
  onRegenerate,
  onEdit,
  onRetry,
  onFollowup,
  onNavigate,
}: MessageListProps) {
  const { t } = useTranslation();
  const toast = useToast();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [atBottom, setAtBottom] = useState(true);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 48);
  };

  // Follow content while pinned to the bottom; leave the view alone when reading back.
  useEffect(() => {
    if (atBottom) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, streamText, streaming, atBottom]);

  const jumpToBottom = () => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    setAtBottom(true);
  };

  function copy(text: string) {
    navigator.clipboard
      ?.writeText(text)
      .then(() => toast.show(t("assistant.copied"), "success"))
      .catch(() => toast.show(t("assistant.errorLine"), "error"));
  }

  const lastAssistantId = [...messages].reverse().find((m) => m.role === "assistant")?.id ?? null;
  const lastAssistant = messages.find((m) => m.id === lastAssistantId);
  const followupKeys: SuggestionKey[] =
    !streaming && !error && lastAssistant
      ? followupsFor((lastAssistant.meta?.used_tool as string | null | undefined) ?? null)
      : [];

  return (
    <div className="conversation__stream">
      <div className="conversation__scroll" ref={scrollRef} onScroll={onScroll}>
        <ul className="conversation__messages">
          {messages.map((m) => {
            const cites = (m.meta?.citations as AskCitation[] | undefined) ?? [];
            const atts = (m.meta?.attachments as AttachmentInfo[] | undefined) ?? [];
            const steps = (m.meta?.steps as ChatStep[] | undefined) ?? [];
            if (m.role === "user") {
              return (
                <li key={m.id} className="msg msg--user">
                  {atts.length > 0 && (
                    <ul className="msg-attach">
                      {atts.map((a) => (
                        <li key={a.id} className="msg-attach__chip">
                          <NavIcon name="reports" />
                          <span className="msg-attach__name" dir="auto">{a.name}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className="msg__text" dir="auto">{m.content}</p>
                  <div className="msg__actions">
                    <Tooltip label={t("assistant.editPrompt")} placement="bottom">
                      <button
                        type="button"
                        className="msg__action"
                        aria-label={t("assistant.editPrompt")}
                        onClick={() => onEdit(m.content)}
                      >
                        <NavIcon name="edit" />
                      </button>
                    </Tooltip>
                  </div>
                </li>
              );
            }
            return (
              <li key={m.id} className="msg msg--assistant">
                {steps.length > 0 && <StepsSummary steps={steps} />}
                <Markdown text={m.content} onNavigate={onNavigate} />
                {cites.length > 0 && (
                  <ul className="assistant-cites msg__cites">
                    {cites.map((c) => (
                      <li key={`${c.type}:${c.value}`}>
                        <CitationLink c={c} onNavigate={onNavigate} />
                      </li>
                    ))}
                  </ul>
                )}
                <div className="msg__actions">
                  <Tooltip label={t("assistant.copy")} placement="bottom">
                    <button
                      type="button"
                      className="msg__action"
                      aria-label={t("assistant.copy")}
                      onClick={() => copy(m.content)}
                    >
                      <NavIcon name="duplicate" />
                    </button>
                  </Tooltip>
                  {m.id === lastAssistantId && !streaming && (
                    <Tooltip label={t("assistant.regenerate")} placement="bottom">
                      <button
                        type="button"
                        className="msg__action"
                        aria-label={t("assistant.regenerate")}
                        onClick={onRegenerate}
                      >
                        <NavIcon name="rotate" />
                      </button>
                    </Tooltip>
                  )}
                </div>
              </li>
            );
          })}

          {streaming && (
            <li className="msg msg--assistant">
              {streamSteps.length > 0 && <StepStack steps={streamSteps} />}
              {streamText ? (
                <div className="msg__streaming">
                  <Markdown text={streamText} onNavigate={onNavigate} />
                  <span className="msg__caret" aria-hidden="true" />
                </div>
              ) : streamSteps.length === 0 ? (
                <p className="conversation__hint">{t("assistant.thinking")}</p>
              ) : null}
            </li>
          )}

          {error && !streaming && (
            <li className="msg msg--assistant">
              <p className="msg__error" dir="auto">{error}</p>
              <button type="button" className="msg__retry" onClick={onRetry}>
                <NavIcon name="rotate" />
                {t("assistant.retry")}
              </button>
            </li>
          )}

          {followupKeys.length > 0 && (
            <li className="msg-followups">
              <ul className="msg-followups__list">
                {followupKeys.map((k) => {
                  const q = t(`assistant.suggestions.${k}`);
                  return (
                    <li key={k}>
                      <button type="button" className="msg-followups__chip" onClick={() => onFollowup(q)}>
                        {q}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </li>
          )}
        </ul>
      </div>

      {!atBottom && (
        <button type="button" className="conversation__jump" onClick={jumpToBottom}>
          <span aria-hidden="true">↓</span> {t("assistant.jumpNew")}
        </button>
      )}
    </div>
  );
}
