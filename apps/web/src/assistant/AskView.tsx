import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { askAssistant, type AskAnswer, type AskCitation } from "../api/assistant";
import { collectContext } from "./context";
import { NavIcon } from "../app/icons";
import { useToast } from "../app/ToastContext";
import { Bdi } from "../components/Bdi";
import { EntityLink } from "../components/EntityLink";
import "../pages/assistant/assistant.css";

// The single-shot ask experience (form + suggestions + answer), shared by the full-page
// /assistant route and the global panel so both render one implementation. The page and the
// panel supply their own header/chrome around it.

const SUGGESTION_KEYS = ["s1", "s2", "s3", "s4"] as const;

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

export function AskView() {
  const { t } = useTranslation();
  const toast = useToast();
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<AskAnswer | null>(null);

  async function submit(q: string) {
    const text = q.trim();
    if (!text || busy) return;
    setBusy(true);
    try {
      setAnswer(await askAssistant(text, collectContext()));
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void submit(question);
  }

  function ask(preset: string) {
    setQuestion(preset);
    void submit(preset);
  }

  return (
    <>
      <form className="card assistant-ask" onSubmit={onSubmit}>
        <textarea
          className="assistant-ask__input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("assistant.placeholder")}
          rows={2}
          dir="auto"
          onKeyDown={(e) => {
            // Enter submits; Shift+Enter for a newline (calm, form-standard).
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit(question);
            }
          }}
        />
        <button type="submit" className="btn btn--primary" disabled={busy || !question.trim()}>
          {busy ? t("assistant.thinking") : t("assistant.ask")}
        </button>
      </form>

      {!answer && !busy && (
        <div className="assistant-suggest">
          <p className="assistant-suggest__label">{t("assistant.tryLabel")}</p>
          <ul className="assistant-suggest__list">
            {SUGGESTION_KEYS.map((k) => (
              <li key={k}>
                <button type="button" className="assistant-suggest__chip" onClick={() => ask(t(`assistant.suggestions.${k}`))}>
                  {t(`assistant.suggestions.${k}`)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {busy && (
        <div className="card assistant-answer" aria-busy="true">
          <p className="assistant-answer__thinking">{t("assistant.thinking")}</p>
        </div>
      )}

      {answer && !busy && (
        <div className="card assistant-answer">
          <p className="assistant-answer__text" dir="auto">{answer.answer}</p>
          {answer.citations.length > 0 && (
            <div className="assistant-answer__sources">
              <p className="assistant-answer__sources-label">{t("assistant.sources")}</p>
              <ul className="assistant-cites">
                {answer.citations.map((c) => (
                  <li key={`${c.type}:${c.value}`}>
                    <CitationLink c={c} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </>
  );
}
