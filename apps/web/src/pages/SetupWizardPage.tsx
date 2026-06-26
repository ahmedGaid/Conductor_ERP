import { useState } from "react";
import { useTranslation } from "react-i18next";

import { getMe } from "../api/identity";
import { completeSetup } from "../api/setup";
import { LanguageSwitcher } from "../app/LanguageSwitcher";
import { ThemeToggle } from "../app/ThemeToggle";
import { useAsync } from "../hooks/useAsync";
import { SYSTEM_ADMIN } from "./settings/roles";
import "./SetupWizardPage.css";

/**
 * First-run setup — placeholder shell (Growth Phase 1.0).
 *
 * A new organization lands here until setup is finished; the post-login route guard
 * (`SetupGate` in App.tsx) sends them here. For now it carries the brand frame plus a single
 * "finish" action so the org can leave the guard without a shell. The real keyboard-first
 * multi-step wizard (company profile → chart of accounts → tax → invite team) replaces the body
 * in slice 1.1; this page only needs to exist and be exitable.
 */
export function SetupWizardPage({ onCompleted }: { onCompleted: () => void }) {
  const { t } = useTranslation();
  const { data: me } = useAsync(getMe, []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  async function onFinish() {
    setBusy(true);
    setError(null);
    try {
      await completeSetup();
      onCompleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="setup">
      <section className="setup__card page-enter">
        <div className="setup__head">
          <div className="setup__brand">
            <span className="setup__logo" aria-hidden="true" />
            <span className="setup__wordmark">{t("app.title")}</span>
          </div>
          <span className="setup__chrome">
            <ThemeToggle />
            <LanguageSwitcher />
          </span>
        </div>

        <h1 className="setup__title">{t("setup.title")}</h1>
        <p className="setup__lede">{t("setup.lede")}</p>

        {isAdmin ? (
          <>
            {error && (
              <p className="setup__error" role="alert">
                {error}
              </p>
            )}
            <div className="setup__actions">
              <button className="btn btn--primary" type="button" onClick={onFinish} disabled={busy}>
                {busy ? t("common.loading") : t("setup.finish")}
              </button>
            </div>
          </>
        ) : (
          <p className="setup__lede">{t("setup.adminOnly")}</p>
        )}
      </section>
    </main>
  );
}
