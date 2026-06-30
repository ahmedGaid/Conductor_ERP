import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Tooltip } from "../components/Tooltip";
import { NavIcon } from "./icons";
import { getTheme, setTheme, type Theme } from "../theme";

// Light/dark toggle for the app chrome. Reuses the ghost icon-button styling already in the command
// bar, so it needs no new CSS. Shows a sun while dark (click → light) and a moon while light.
export function ThemeToggle() {
  const { t } = useTranslation();
  const [theme, setThemeState] = useState<Theme>(getTheme());

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  }

  const goingDark = theme !== "dark";
  const label = t(goingDark ? "theme.toDark" : "theme.toLight");

  return (
    <Tooltip label={label} placement="bottom">
      <button
        type="button"
        className="btn btn--ghost btn--icon"
        aria-pressed={theme === "dark"}
        aria-label={label}
        onClick={toggle}
      >
        <NavIcon name={theme === "dark" ? "sun" : "moon"} />
      </button>
    </Tooltip>
  );
}
