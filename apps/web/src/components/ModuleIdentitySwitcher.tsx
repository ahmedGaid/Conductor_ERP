import { useTranslation } from "react-i18next";

import { useModuleIdentity, type ModuleIdentityMode } from "../hooks/useModuleIdentity";
import "./documentDetail.css";

const MODES: readonly ModuleIdentityMode[] = ["mono", "accent", "tag"];

/**
 * TEMPORARY evaluation control: flips the module-identity preview mode (mono / accent / tag) live on
 * the real app so the founder can compare all three and pick one. Removed once a mode is chosen. It
 * writes a shared store, so every open document detail page updates at once.
 */
export function ModuleIdentitySwitcher() {
  const { t } = useTranslation();
  const [mode, setMode] = useModuleIdentity();
  return (
    <div className="docidentity-switch" role="group" aria-label={t("document.identityPreview.label")}>
      <span className="docidentity-switch__label">{t("document.identityPreview.label")}</span>
      <div className="docidentity-switch__seg">
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            className="docidentity-switch__btn"
            aria-pressed={mode === m}
            onClick={() => setMode(m)}
          >
            {t(`document.identityPreview.${m}`)}
          </button>
        ))}
      </div>
    </div>
  );
}
