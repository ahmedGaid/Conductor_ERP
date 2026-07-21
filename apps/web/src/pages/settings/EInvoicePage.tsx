import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  getETAConfig,
  saveETAConfig,
  testETAConnection,
  type ETAConfig,
  type ETAConfigUpdate,
  type ETATestResult,
} from "../../api/einvoice";
import { getMe } from "../../api/identity";
import { NavIcon } from "../../app/icons";
import { useAsync } from "../../hooks/useAsync";
import { relativeTime } from "../../lib/relativeTime";
import { Bdi } from "../../components/Bdi";
import { SettingsNav } from "./SettingsNav";
import { SettingsSkeleton } from "./ProfilePage";
import { SYSTEM_ADMIN } from "./roles";
import { Segmented, SettingRow, Toggle } from "./controls";
// The simulated-adapter notice below uses the shared `.sysbanner` recipe; import its stylesheet so a
// direct load of this page (no prior visit to Settings → System) still sizes the icon and lays the
// banner out — otherwise the warning glyph renders unsized (full-width triangle).
import "./system.css";

// The plaintext secret is never returned by the API. While `has_secret` is true we show this
// placeholder so the admin knows one is stored without ever seeing it; leaving the field blank on
// save keeps the stored value.
const SECRET_PLACEHOLDER = "••••••••••••";

export function EInvoicePage() {
  const { t, i18n } = useTranslation();
  const { data: me } = useAsync(getMe, []);
  const { data: loaded, reload } = useAsync(getETAConfig, []);

  const [cfg, setCfg] = useState<ETAConfig | null>(null);
  const [secret, setSecret] = useState("");        // only what the admin types this session
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ETATestResult | null>(null);

  useEffect(() => {
    if (loaded) setCfg(loaded);
  }, [loaded]);

  const isAdmin = me?.roles?.includes(SYSTEM_ADMIN) ?? false;

  if (me && !isAdmin) {
    return (
      <section className="page-enter">
        <SettingsNav />
        <div className="card setcard">
          <p className="muted">{t("settings.einvoice.adminOnly")}</p>
        </div>
      </section>
    );
  }
  if (!cfg) return <SettingsSkeleton />;

  function edit(changes: Partial<ETAConfig>) {
    setCfg((cur) => (cur ? { ...cur, ...changes } : cur));
    setResult(null);   // any edit invalidates a prior test result
  }

  async function persist(changes: ETAConfigUpdate) {
    setBusy(true);
    setErr(null);
    try {
      const saved = await saveETAConfig(changes);
      setCfg(saved);
      setSecret("");
      setResult(null);
      return saved;
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function onSave() {
    if (!cfg) return;
    const changes: ETAConfigUpdate = {
      environment: cfg.environment,
      identity_url: cfg.identity_url,
      api_base_url: cfg.api_base_url,
      client_id: cfg.client_id,
      rin: cfg.rin,
      enabled: cfg.enabled,
    };
    if (secret.trim()) changes.client_secret = secret;
    await persist(changes);
  }

  async function onClearSecret() {
    await persist({ clear_secret: true });
  }

  async function onTest() {
    setTesting(true);
    setResult(null);
    try {
      setResult(await testETAConnection());
      await reload();
    } catch (e) {
      setResult({ ok: false, reason: "auth_failed", detail: e instanceof Error ? e.message : String(e) });
    } finally {
      setTesting(false);
    }
  }

  return (
    <section className="page-enter">
      <SettingsNav />
      <div className="card setcard">
        <p className="setrow__desc setcard__lead">{t("settings.einvoice.lead")}</p>

        {/* The submission adapter is still simulated — never let the screen imply live filing. */}
        {cfg.simulated && (
          <div className="sysbanner sysbanner--warning" role="status">
            <NavIcon name="warning" />
            <span>{t("settings.einvoice.simulatedNote")}</span>
          </div>
        )}

        <SettingRow title={t("settings.einvoice.environment")} desc={t("settings.einvoice.environmentDesc")}>
          <Segmented
            ariaLabel={t("settings.einvoice.environment")}
            value={cfg.environment || "sandbox"}
            onChange={(v) => edit({ environment: v as ETAConfig["environment"] })}
            options={[
              { value: "sandbox", label: t("settings.einvoice.envSandbox") },
              { value: "production", label: t("settings.einvoice.envProduction") },
            ]}
          />
        </SettingRow>

        <SettingRow title={t("settings.einvoice.identityUrl")} desc={t("settings.einvoice.identityUrlDesc")} htmlFor="eta-identity">
          <input
            id="eta-identity"
            type="url"
            className="latin"
            dir="ltr"
            placeholder="https://id.preprod.eta.gov.eg"
            value={cfg.identity_url}
            onChange={(e) => edit({ identity_url: e.target.value })}
          />
        </SettingRow>

        <SettingRow title={t("settings.einvoice.apiUrl")} desc={t("settings.einvoice.apiUrlDesc")} htmlFor="eta-api">
          <input
            id="eta-api"
            type="url"
            className="latin"
            dir="ltr"
            placeholder="https://api.preprod.invoicing.eta.gov.eg"
            value={cfg.api_base_url}
            onChange={(e) => edit({ api_base_url: e.target.value })}
          />
        </SettingRow>

        <SettingRow title={t("settings.einvoice.clientId")} htmlFor="eta-client-id">
          <input
            id="eta-client-id"
            type="text"
            className="latin"
            dir="ltr"
            value={cfg.client_id}
            onChange={(e) => edit({ client_id: e.target.value })}
          />
        </SettingRow>

        <SettingRow title={t("settings.einvoice.clientSecret")} desc={t("settings.einvoice.clientSecretDesc")} htmlFor="eta-secret">
          <div className="eta-secret">
            <input
              id="eta-secret"
              type="password"
              className="latin"
              dir="ltr"
              autoComplete="new-password"
              placeholder={cfg.has_secret ? SECRET_PLACEHOLDER : t("settings.einvoice.clientSecretEmpty")}
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
            />
            {cfg.has_secret && (
              <button type="button" className="btn btn--sm btn--ghost" onClick={onClearSecret} disabled={busy}>
                {t("settings.einvoice.clearSecret")}
              </button>
            )}
          </div>
        </SettingRow>

        <SettingRow title={t("settings.einvoice.rin")} desc={t("settings.einvoice.rinDesc")} htmlFor="eta-rin">
          <input
            id="eta-rin"
            type="text"
            className="latin"
            dir="ltr"
            inputMode="numeric"
            value={cfg.rin}
            onChange={(e) => edit({ rin: e.target.value })}
          />
        </SettingRow>

        <SettingRow title={t("settings.einvoice.enabled")} desc={t("settings.einvoice.enabledDesc")}>
          <Toggle
            checked={cfg.enabled}
            onChange={(v) => edit({ enabled: v })}
            label={t("settings.einvoice.enabled")}
          />
        </SettingRow>

        {/* Status line: where the config in force comes from + last successful test. */}
        <div className="setcard__block eta-status">
          <SettingRow title={t("settings.einvoice.source")}>
            <span className="muted">{t(`settings.einvoice.sourceValue.${cfg.source}`)}</span>
          </SettingRow>
          <SettingRow title={t("settings.einvoice.lastTest")}>
            <span className="muted">
              {cfg.last_test_ok_at ? relativeTime(cfg.last_test_ok_at, i18n.language) : t("settings.einvoice.lastTestNever")}
            </span>
          </SettingRow>
        </div>

        {err && <p className="setrow__desc eta-error" role="alert">{err}</p>}

        {result && (
          <div className={`eta-result eta-result--${result.ok ? "ok" : "fail"}`} role="status">
            <NavIcon name={result.ok ? "checkCircle" : "warning"} />
            <span>
              {result.ok ? t("settings.einvoice.testOk") : t(`settings.einvoice.testFail.${result.reason}`)}
              {!result.ok && result.detail ? <> — <Bdi>{result.detail}</Bdi></> : null}
            </span>
          </div>
        )}

        <div className="setcard__block eta-actions">
          <button type="button" className="btn btn--primary btn--sm" onClick={onSave} disabled={busy}>
            {busy ? t("settings.einvoice.saving") : t("settings.einvoice.save")}
          </button>
          <button type="button" className="btn btn--sm" onClick={onTest} disabled={testing || busy}>
            {testing ? t("settings.einvoice.testing") : t("settings.einvoice.test")}
          </button>
        </div>
      </div>
    </section>
  );
}
