import { useTranslation } from "react-i18next";

import { ConversationView } from "../../assistant/ConversationView";
import { ThreadList } from "../../assistant/ThreadList";
import { useAssistant } from "../../assistant/AssistantProvider";
import { NavIcon } from "../../app/icons";
import { Tooltip } from "../../components/Tooltip";
import { EmptyState } from "../../components/EmptyState";
import "./assistant.css";

// The fullscreen workspace: a thread-history rail on the inline-start edge and the active
// conversation filling the rest. Both columns read the one shared list/selection from the provider,
// so the panel and this page never disagree.
export function AssistantPage() {
  const { t } = useTranslation();
  const { setConversationId, enabled } = useAssistant();

  if (!enabled) {
    return (
      <section className="assistant-page">
        <EmptyState
          title={t("assistant.disabledTitle")}
          hint={t("assistant.disabledHint")}
          icon={<NavIcon name="sparkle" />}
        />
      </section>
    );
  }

  return (
    <section className="assistant-page assistant-page--workspace">
      <aside className="assistant-workspace__rail" aria-label={t("assistant.threads.title")}>
        <ThreadList />
      </aside>
      <div className="assistant-workspace__main">
        <header className="assistant-head">
          <span className="assistant-head__icon" aria-hidden="true">
            <NavIcon name="sparkle" />
          </span>
          <div>
            <h1 className="assistant-head__title">{t("assistant.title")}</h1>
            <p className="assistant-head__subtitle">{t("assistant.subtitle")}</p>
          </div>
          <Tooltip label={t("assistant.threads.new")} placement="bottom">
            <button
              type="button"
              className="assistant-head__new"
              aria-label={t("assistant.threads.new")}
              onClick={() => setConversationId(null)}
            >
              <NavIcon name="plus" />
            </button>
          </Tooltip>
        </header>
        <ConversationView />
      </div>
    </section>
  );
}
