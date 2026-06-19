import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { LanguageSwitcher } from "../app/LanguageSwitcher";
import { ThemeToggle } from "../app/ThemeToggle";
import "./LoginPage.css";

export function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [needsOtp, setNeedsOtp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await login(username, password, needsOtp ? otp : undefined);
      if (result.twofa_required) {
        setNeedsOtp(true);
        setError(t("login.otpRequired"));
        return;
      }
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <form className="login__card" onSubmit={onSubmit}>
        <div className="login__head">
          <div className="login__brand">
            <span className="login__logo" aria-hidden="true">C</span>
            <span className="login__wordmark">{t("app.title")}</span>
          </div>
          <span className="login__chrome">
            <ThemeToggle />
            <LanguageSwitcher />
          </span>
        </div>
        <p className="login__subtitle">{t("login.subtitle")}</p>

        <label className="login__field">
          <span>{t("login.username")}</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>

        <label className="login__field">
          <span>{t("login.password")}</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {needsOtp && (
          <label className="login__field">
            <span>{t("login.otp")}</span>
            <input value={otp} onChange={(e) => setOtp(e.target.value)} inputMode="numeric" />
          </label>
        )}

        {error && (
          <p className="login__error" role="alert">
            {error}
          </p>
        )}

        <button className="btn btn--primary login__submit" type="submit" disabled={busy}>
          {busy ? t("common.loading") : t("login.submit")}
        </button>
      </form>
    </main>
  );
}
