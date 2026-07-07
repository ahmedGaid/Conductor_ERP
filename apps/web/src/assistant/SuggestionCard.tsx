import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { AssistantSuggestion, SuggestionCandidate, SuggestionOption } from "../api/assistant";
import { NavIcon } from "../app/icons";
import { Bdi } from "../components/Bdi";

// Blocker entity → its home-module icon (same hand as citations / action records).
const ENTITY_ICON: Record<string, string> = {
  customer: "crm",
  supplier: "purchasing",
  item: "inventory",
  warehouse: "inventory",
};

/**
 * A blocker turned actionable (plan session 12): the issue in one plain sentence, then only the
 * ways out the server says this user may take — create it inline (stays in chat, runs the normal
 * propose→confirm flow), jump to the create form prefilled (the panel stays open so the promise
 * "I'll bring you back and continue" holds), or pick one of the near matches. No permission means
 * calm text and zero buttons — unavailable is never greyed out. Session 13 flips it to resolved.
 */
export function SuggestionCard({
  suggestion,
  onFollowup,
}: {
  suggestion: AssistantSuggestion;
  onFollowup: (question: string) => void;
}) {
  const { t } = useTranslation();
  const { issue, options, no_permission: noPermission, resume } = suggestion;
  const entityName = t(`assistant.suggest.entity.${issue.entity}`, issue.entity);
  const icon = ENTITY_ICON[issue.entity] ?? "sparkle";

  // Resolved (session 13 flips it): settled like a consumed ActionCard, reload-safe via meta.
  if (suggestion.status === "resolved") {
    return (
      <div className="action-card action-card--done">
        <p className="action-card__result" dir="auto">
          <NavIcon name="checkCircle" />
          {t("assistant.suggest.resolved")}
        </p>
      </div>
    );
  }

  function pickCandidate(c: SuggestionCandidate) {
    onFollowup(t("assistant.suggest.useCandidate", { name: c.name, code: c.code }));
  }

  function runInline(option: SuggestionOption) {
    // "Create it from here" re-enters the loop as a plain ask; the planner proposes the
    // session-10 action and the familiar confirm card takes over — one write path, no second one.
    const name = String(option.args?.query ?? issue.query);
    onFollowup(t("assistant.suggest.createCommand", { entity: entityName, name }));
  }

  return (
    <div className="action-card suggest-card">
      <header className="action-card__head">
        <span className="action-card__icon" aria-hidden="true">
          <NavIcon name={icon} />
        </span>
        <span className="action-card__title">
          {/* A blocker can arrive with no name at all (e.g. no warehouse exists yet) — quoting an
              empty string reads broken, so the bare variant drops the quote entirely. */}
          {t(
            issue.query ? `assistant.suggest.${issue.kind}` : "assistant.suggest.missingBare",
            { entity: entityName, query: issue.query },
          )}
        </span>
      </header>

      {noPermission ? (
        // Blame-free and quiet: what to do instead, with zero dead buttons.
        <p className="suggest-card__blocked" dir="auto">{t("assistant.suggest.noPermission")}</p>
      ) : (
        <div className="suggest-card__options">
          {options.map((option, i) => {
            if (option.kind === "inline_action") {
              return (
                <button
                  key={i}
                  type="button"
                  className="action-card__confirm"
                  onClick={() => runInline(option)}
                >
                  {t("assistant.suggest.create", { entity: entityName })}
                </button>
              );
            }
            if (option.kind === "deep_link" || option.kind === "open_record") {
              // A real link; the panel stays open across the route change so the paused work —
              // and the promise to continue it — survives the detour.
              return (
                <Link key={i} className="suggest-card__link" to={option.to ?? "/"}>
                  <NavIcon name={icon} />
                  {t(option.label_key ?? "assistant.suggest.open", { entity: entityName })}
                  <span className="suggest-card__out" aria-hidden="true">↗</span>
                </Link>
              );
            }
            // review_candidates: compact near-match list, pick-one maps it and continues.
            return (
              <div key={i} className="suggest-card__review">
                <span className="action-card__risks-label">{t("assistant.suggest.review")}</span>
                <ul className="suggest-card__candidates">
                  {(option.candidates ?? []).map((c) => (
                    <li key={c.code}>
                      <button
                        type="button"
                        className="suggest-card__candidate"
                        onClick={() => pickCandidate(c)}
                      >
                        <Bdi>{c.name}</Bdi>
                        <span className="suggest-card__code latin">{c.code}</span>
                        <span className="suggest-card__score latin">
                          {Math.round(c.score * 100)}%
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}

      {resume && (
        <p className="suggest-card__resume" dir="auto">
          {t("assistant.suggest.afterResume", { resume })}
        </p>
      )}
    </div>
  );
}
