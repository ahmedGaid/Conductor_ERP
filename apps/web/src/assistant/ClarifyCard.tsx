import { useTranslation } from "react-i18next";

import type { AssistantClarify, ClarifyOption } from "../api/assistant";
import { NavIcon } from "../app/icons";
import { Bdi } from "../components/Bdi";

/**
 * A parked clarifying question (ai-reliability T5.10) — the conversational twin of the confirm card.
 *
 * The run is waiting, not finished: whatever it already gathered is held server-side, and answering
 * continues that same run. Options are a shortcut past typing (two to four, at most one marked as
 * the recommended one); the composer stays open underneath for an answer nobody listed, which is
 * why there is no "other" button here — free text is the composer's job, not a fifth option.
 *
 * Answered is a settled state, like a consumed proposal: the card keeps the question and shows what
 * was picked, so a reload reads the way the conversation happened.
 */
export function ClarifyCard({
  clarify,
  messageId,
  onAnswer,
  disabled,
}: {
  clarify: AssistantClarify;
  messageId: number;
  onAnswer: (messageId: number, answer: string) => void;
  // A stream is already running (this card's own answer, or another turn) — the options stay
  // visible and readable, never disappear, but a second tap can't fork the run.
  disabled?: boolean;
}) {
  const { t } = useTranslation();

  if (clarify.status === "answered") {
    return (
      <div className="action-card action-card--done">
        <p className="action-card__result" dir="auto">
          <NavIcon name="checkCircle" />
          {clarify.answer
            ? t("assistant.clarify.answered", { answer: clarify.answer })
            : t("assistant.clarify.answeredBare")}
        </p>
      </div>
    );
  }

  // An optimistic (negative) message id has no server-side card to answer against yet — the
  // question still reads fine, it just waits for the settled row rather than offering dead buttons.
  const answerable = messageId > 0 && !disabled;

  return (
    <div className="action-card clarify-card">
      <header className="action-card__head">
        <span className="action-card__icon" aria-hidden="true">
          <NavIcon name="sparkle" />
        </span>
        <span className="action-card__title" dir="auto">
          <Bdi>{clarify.question}</Bdi>
        </span>
      </header>

      {clarify.options.length > 0 && (
        <div className="clarify-card__options" role="group" aria-label={clarify.question}>
          {clarify.options.map((option: ClarifyOption) => (
            <button
              key={option.label}
              type="button"
              className={
                option.recommended
                  ? "clarify-card__option clarify-card__option--recommended"
                  : "clarify-card__option"
              }
              disabled={!answerable}
              onClick={() => onAnswer(messageId, option.label)}
            >
              <span className="clarify-card__label">
                <Bdi>{option.label}</Bdi>
                {option.recommended && (
                  <span className="clarify-card__badge">{t("assistant.clarify.recommended")}</span>
                )}
              </span>
              {option.description && (
                <span className="clarify-card__description" dir="auto">
                  <Bdi>{option.description}</Bdi>
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {clarify.allow_free_text && (
        <p className="clarify-card__free" dir="auto">{t("assistant.clarify.freeText")}</p>
      )}
    </div>
  );
}
