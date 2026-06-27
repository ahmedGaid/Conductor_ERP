import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Popover } from "../components/Popover";

/**
 * The foot of the sidebar — the workspace tier. A single company chip (the workspace) that opens
 * company-wide actions. Personal account actions live in the top-bar user menu, not here. The menu
 * flips open upward (the chip sits at the bottom of the viewport — the Popover handles the flip).
 */
export function SidebarIdentity({
  companyName,
  isAdmin,
}: {
  companyName: string;
  isAdmin: boolean;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const companyRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);

  const go = (to: string) => {
    setOpen(false);
    navigate(to);
  };

  return (
    <div className="sidebar__identity">
      <button
        ref={companyRef}
        type="button"
        className="sidebar__company"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {/* Just the leading letter in the collapsed rail, where the full name is hidden. */}
        <span className="sidebar__company-initial" aria-hidden="true">
          {companyName.charAt(0)}
        </span>
        <span className="sidebar__company-name">{companyName}</span>
      </button>
      <Popover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={companyRef}
        className="appmenu"
        ariaLabel={companyName}
      >
        <div className="appmenu__head">
          <span className="appmenu__workspace">{companyName}</span>
        </div>
        <button className="appmenu__item" type="button" onClick={() => go("/settings/organization")}>
          {t("settings.tabs.organization")}
        </button>
        {isAdmin && (
          <button className="appmenu__item" type="button" onClick={() => go("/admin/users")}>
            {t("nav.usersAdmin")}
          </button>
        )}
        {isAdmin && (
          <button className="appmenu__item" type="button" onClick={() => go("/admin/roles")}>
            {t("nav.rolesAdmin")}
          </button>
        )}
      </Popover>
    </div>
  );
}
