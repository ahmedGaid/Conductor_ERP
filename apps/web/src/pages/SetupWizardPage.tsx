import { useState } from "react";
import { useTranslation } from "react-i18next";

import { getMe } from "../api/identity";
import {
  completeSetup,
  seedChartOfAccounts,
  type ChartOfAccountsState,
  type SetupStatus,
} from "../api/setup";
import { LanguageSwitcher } from "../app/LanguageSwitcher";
import { ThemeToggle } from "../app/ThemeToggle";
import { useAsync } from "../hooks/useAsync";
import { SYSTEM_ADMIN } from "./settings/roles";
import "./SetupWizardPage.css";

const CheckIcon = (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

/**
 * First-run setup wizard (Growth Phase 1.x).
 *
 * A new organization lands here until setup is finished; the post-login route guard
 * (`SetupGate` in App.tsx) sends them here. Slice 1.2 adds the first real step — provisioning the
 * chart of accounts in one click (reuses accounting's own seeding via `/setup/chart-of-accounts`).
 * The company profile / tax / invite-team steps and the multi-step shell land in later slices.
 */
export function SetupWizardPage({
  status,
  onCompleted,
}: {
  status: SetupStatus;
  onCompleted: () => void;
}) {
  const { t } = useTranslation();
  const { data: me } = useAsync(getMe, []);
  const [coa, setCoa] = useState<ChartOfAccountsState>(status.chart_of_accounts);
  const [busy, setBusy] = useState<null | "coa" | "finish">(null);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  async function onSeedCoa() {
    setBusy("coa");
    setError(null);
    try {
      setCoa(await seedChartOfAccounts());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function onFinish() {
    setBusy("finish");
    setError(null);
    try {
      await completeSetup();
      onCompleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(null);
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
            <div className="setup__step">
              <div className="setup__step-head">
                <span className="setup__step-title">{t("setup.coa.title")}</span>
                {coa.seeded && (
                  <span className="setup__badge">
                    <span className="setup__badge-icon">{CheckIcon}</span>
                    {t("setup.coa.ready", { n: coa.accounts })}
                  </span>
                )}
              </div>
              <p className="setup__step-lede">{t("setup.coa.lede")}</p>
              {!coa.seeded && (
                <div className="setup__actions">
                  <button
                    className="btn btn--primary"
                    type="button"
                    onClick={onSeedCoa}
                    disabled={busy !== null}
                  >
                    {busy === "coa" ? t("setup.coa.seeding") : t("setup.coa.action")}
                  </button>
                </div>
              )}
            </div>

            {error && (
              <p className="setup__error" role="alert">
                {error}
              </p>
            )}

            {coa.seeded && (
              <div className="setup__actions">
                <button
                  className="btn btn--primary"
                  type="button"
                  onClick={onFinish}
                  disabled={busy !== null}
                >
                  {busy === "finish" ? t("common.loading") : t("setup.finish")}
                </button>
              </div>
            )}
          </>
        ) : (
          <p className="setup__lede">{t("setup.adminOnly")}</p>
        )}
      </section>
    </main>
  );
}
