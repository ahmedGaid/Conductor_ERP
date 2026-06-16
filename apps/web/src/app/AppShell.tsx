import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { CommandBar } from "./CommandBar";
import "./AppShell.css";

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const location = useLocation();

  return (
    <div className="appshell">
      <a className="appshell__skip" href="#main">
        {t("shell.skipToContent")}
      </a>
      <Sidebar />
      <CommandBar />
      <main id="main" className="appshell__main">
        {/* Re-keying on the path replays the enter animation each navigation,
            so pages glide in instead of snapping. */}
        <div key={location.pathname} className="appshell__content page-enter">
          {children}
        </div>
      </main>
    </div>
  );
}
