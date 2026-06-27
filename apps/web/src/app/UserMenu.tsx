import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { getMe } from "../api/identity";
import { useAuth } from "../auth/AuthContext";
import { usePreferences } from "../preferences/PreferencesContext";
import { useAsync } from "../hooks/useAsync";
import { Popover } from "../components/Popover";
import { Tooltip } from "../components/Tooltip";
import "./AppMenu.css";

/** Two-letter monogram for the account avatar — first+last initial, or first two letters. */
function monogram(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * The personal account menu in the top bar (beside notifications). The avatar + name open a menu of
 * personal actions — settings and sign out. Company-wide actions live on the workspace chip in the
 * sidebar; product preferences live in the "⋮" menu.
 */
export function UserMenu() {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const { prefs } = usePreferences();
  const { data: me } = useAsync(getMe, [], "me");
  const navigate = useNavigate();
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);

  const name = prefs?.display_name || me?.username || "—";
  const role = me?.roles?.[0] ?? "";

  return (
    <>
      <Tooltip label={name} placement="bottom">
        <button
          ref={triggerRef}
          type="button"
          className="usermenu__trigger"
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-label={name}
          onClick={() => setOpen((o) => !o)}
        >
          <span className="usermenu__avatar" aria-hidden="true">
            {monogram(name)}
          </span>
          <span className="usermenu__name latin">{name}</span>
        </button>
      </Tooltip>

      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={triggerRef}
        className="appmenu"
        ariaLabel={name}
      >
        <div className="appmenu__head">
          <span className="appmenu__workspace">{name}</span>
          {role && <span className="appmenu__user">{role}</span>}
        </div>
        <button
          className="appmenu__item"
          type="button"
          onClick={() => {
            setOpen(false);
            navigate("/settings/profile");
          }}
        >
          {t("settings.title")}
        </button>
        <div className="appmenu__sep" role="separator" />
        <button
          className="appmenu__item"
          type="button"
          onClick={() => {
            setOpen(false);
            logout();
          }}
        >
          {t("shell.logout")}
        </button>
      </Popover>
    </>
  );
}
