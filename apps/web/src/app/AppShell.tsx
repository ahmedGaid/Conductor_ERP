import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Sidebar } from "./Sidebar";
import { CommandBar } from "./CommandBar";
import "./AppShell.css";

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();

  return (
    <div className="appshell">
      <a className="appshell__skip" href="#main">
        {t("shell.skipToContent")}
      </a>
      <Sidebar />
      <CommandBar />
      <main id="main" className="appshell__main">
        <div className="appshell__content">{children}</div>
      </main>
    </div>
  );
}
