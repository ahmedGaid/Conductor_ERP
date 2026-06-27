import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { getMe, getOrgPreferences, patchOrgPreferences, type OrgPreferences } from "../api/identity";
import {
  completeSetup,
  inviteTeamMember,
  seedChartOfAccounts,
  setTaxSettings,
  type ChartOfAccountsState,
  type InvitedUser,
  type SetupStatus,
  type TaxState,
} from "../api/setup";
import { LanguageSwitcher } from "../app/LanguageSwitcher";
import { ThemeToggle } from "../app/ThemeToggle";
import { SegmentedControl } from "../components/SegmentedControl";
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
 * (`SetupGate` in App.tsx) sends them here. Steps so far: company profile (1.3, writes to the same
 * OrgPreferences a user edits later in Settings → Organization) and the one-click chart of accounts
 * (1.2). The multi-step shell, tax and invite-team steps land in later slices.
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
  const { data: loadedOrg } = useAsync(getOrgPreferences, []);
  const [org, setOrg] = useState<OrgPreferences | null>(null);
  const [coa, setCoa] = useState<ChartOfAccountsState>(status.chart_of_accounts);
  const [tax, setTax] = useState<TaxState>(status.tax);
  const [vatInput, setVatInput] = useState(String(status.tax.vat_rate_bps / 100));
  const [busy, setBusy] = useState<null | "coa" | "invite" | "finish">(null);
  const [error, setError] = useState<string | null>(null);

  // Invite-team step — optional. Each invited member surfaces a one-time temp password to hand over.
  const [inviteUsername, setInviteUsername] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("");
  const [invited, setInvited] = useState<InvitedUser[]>([]);

  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  useEffect(() => {
    if (loadedOrg) setOrg(loadedOrg);
  }, [loadedOrg]);

  // Profile writes go straight to the durable org-preferences surface (one source of truth).
  function commit(changes: Partial<OrgPreferences>) {
    setError(null);
    patchOrgPreferences(changes)
      .then((saved) => setOrg(saved))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }

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

  function commitTax(changes: Partial<TaxState>) {
    setError(null);
    setTaxSettings(changes)
      .then((next) => {
        setTax(next);
        setVatInput(String(next.vat_rate_bps / 100));
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }

  function commitVatRate() {
    const pct = Number(vatInput);
    if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
      setVatInput(String(tax.vat_rate_bps / 100)); // revert bad input
      return;
    }
    const bps = Math.round(pct * 100);
    if (bps !== tax.vat_rate_bps) commitTax({ vat_rate_bps: bps });
  }

  // Whether the invite form holds a complete, not-yet-added member.
  const pendingInvite = inviteUsername.trim() !== "" && inviteEmail.trim() !== "";

  // Sends the form's member and clears it. Throws on failure so callers can stop (don't swallow).
  async function sendInvite() {
    const member = await inviteTeamMember({
      username: inviteUsername.trim(),
      email: inviteEmail.trim(),
      role: inviteRole || undefined,
    });
    setInvited((prev) => [...prev, member]);
    setInviteUsername("");
    setInviteEmail("");
    setInviteRole("");
  }

  async function onInvite(e: FormEvent) {
    e.preventDefault();
    if (!pendingInvite) return;
    setBusy("invite");
    setError(null);
    try {
      await sendInvite();
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
      // Don't silently drop a filled-in invite — add it before finishing. If it fails (e.g. a
      // duplicate), stop here and surface the error so the user can fix it rather than lose it.
      if (pendingInvite) await sendInvite();
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
            {/* Step — company profile */}
            <div className="setup__step">
              <span className="setup__step-title">{t("setup.profile.title")}</span>
              <p className="setup__step-lede">{t("setup.profile.lede")}</p>
              {org && (
                <div className="setup__fields">
                  <label className="setup__field">
                    <span>{t("settings.org.companyName")}</span>
                    <input
                      type="text"
                      value={org.company_name}
                      placeholder={t("setup.profile.companyPlaceholder")}
                      onChange={(e) => setOrg({ ...org, company_name: e.target.value })}
                      onBlur={(e) => commit({ company_name: e.target.value })}
                    />
                  </label>
                  <label className="setup__field">
                    <span>{t("settings.org.country")}</span>
                    <input
                      type="text"
                      value={org.country}
                      onChange={(e) => setOrg({ ...org, country: e.target.value })}
                      onBlur={(e) => commit({ country: e.target.value })}
                    />
                  </label>
                  <label className="setup__field">
                    <span>{t("settings.org.vatNumber")}</span>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={org.vat_number}
                      placeholder={t("setup.profile.vatPlaceholder")}
                      onChange={(e) => setOrg({ ...org, vat_number: e.target.value })}
                      onBlur={(e) => commit({ vat_number: e.target.value })}
                    />
                  </label>
                  <div className="setup__field">
                    <span>{t("settings.org.language")}</span>
                    <SegmentedControl
                      ariaLabel={t("settings.org.language")}
                      value={org.default_language}
                      onChange={(v) => {
                        setOrg({ ...org, default_language: v });
                        commit({ default_language: v });
                      }}
                      options={[
                        { value: "ar", label: "العربية" },
                        { value: "en", label: "English" },
                      ]}
                    />
                  </div>
                  <div className="setup__field">
                    <span>{t("settings.org.baseCurrency")}</span>
                    <span className="muted">{org.base_currency}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Step — chart of accounts */}
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

            {/* Step — tax & e-invoicing */}
            <div className="setup__step">
              <span className="setup__step-title">{t("setup.tax.title")}</span>
              <p className="setup__step-lede">{t("setup.tax.lede")}</p>
              <div className="setup__fields">
                <label className="setup__field setup__field--inline">
                  <span>{t("setup.tax.vatRate")}</span>
                  <span className="setup__suffixed">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step="0.5"
                      value={vatInput}
                      onChange={(e) => setVatInput(e.target.value)}
                      onBlur={commitVatRate}
                    />
                    <span aria-hidden="true">%</span>
                  </span>
                </label>
                <label className="setup__field setup__field--inline">
                  <span>
                    {t("setup.tax.einvoice")}
                    <span className="setup__field-hint">{t("setup.tax.einvoiceHint")}</span>
                  </span>
                  <input
                    type="checkbox"
                    role="switch"
                    checked={tax.einvoice_enabled}
                    onChange={(e) => {
                      setTax({ ...tax, einvoice_enabled: e.target.checked });
                      commitTax({ einvoice_enabled: e.target.checked });
                    }}
                  />
                </label>
              </div>
            </div>

            {/* Step — invite team (optional) */}
            <div className="setup__step">
              <span className="setup__step-title">{t("setup.invite.title")}</span>
              <p className="setup__step-lede">{t("setup.invite.lede")}</p>
              <form className="setup__invite-form" onSubmit={onInvite}>
                <label className="setup__field">
                  <span>{t("admin.invite.username")}</span>
                  <input
                    type="text"
                    value={inviteUsername}
                    onChange={(e) => setInviteUsername(e.target.value)}
                  />
                </label>
                <label className="setup__field">
                  <span>{t("admin.invite.email")}</span>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                  />
                </label>
                <label className="setup__field">
                  <span>{t("admin.users.role")}</span>
                  <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                    <option value="">{t("admin.invite.noRole")}</option>
                    {status.available_roles.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="setup__invite-foot">
                  {pendingInvite && (
                    <span className="setup__field-hint">{t("setup.invite.pendingHint")}</span>
                  )}
                  <button
                    className="btn"
                    type="submit"
                    disabled={busy !== null || !pendingInvite}
                  >
                    {busy === "invite" ? t("common.loading") : t("admin.invite.submit")}
                  </button>
                </div>
              </form>
              {invited.length > 0 && (
                <ul className="setup__invited">
                  {invited.map((m) => (
                    <li key={m.id} className="setup__invited-row">
                      <span className="setup__invited-who">
                        {m.username}
                        {m.role && <span className="muted"> · {m.role}</span>}
                      </span>
                      <span className="setup__invited-pw">
                        <span className="setup__field-hint">{t("setup.invite.tempPassword")}</span>
                        <code>{m.temp_password}</code>
                      </span>
                    </li>
                  ))}
                </ul>
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
