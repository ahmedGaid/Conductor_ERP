import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { CommandBar } from "./CommandBar";
import { Toaster } from "./Toaster";
import { ToastProvider } from "./ToastContext";
import { HelpCenter } from "../help/HelpCenter";
import { HelpProvider } from "../help/HelpContext";
import "./AppShell.css";

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const location = useLocation();
  // On narrow widths the sidebar is an off-canvas drawer; on wide it's always shown
  // and this flag is inert (CSS only reacts to it under the breakpoint).
  const [navOpen, setNavOpen] = useState(false);
  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);

  // Close the drawer whenever we navigate, so picking a destination dismisses it.
  useEffect(() => setNavOpen(false), [location.pathname]);

  // On navigation, move focus to the top of the new page (its heading, or the main
  // region as a fallback) so keyboard and screen-reader users land on the fresh
  // content instead of being stranded on the link they activated. Skips the initial
  // load so we don't yank focus on app boot. The temporary tabindex is dropped on
  // blur to keep the heading out of the normal tab order; programmatic focus doesn't
  // trip :focus-visible, so no stray outline appears.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const main = mainRef.current;
    if (!main) return;
    const raf = window.requestAnimationFrame(() => {
      const target = main.querySelector<HTMLElement>("h1, h2") ?? main;
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
      target.addEventListener("blur", () => target.removeAttribute("tabindex"), { once: true });
    });
    return () => window.cancelAnimationFrame(raf);
  }, [location.pathname]);

  return (
    <ToastProvider>
      <HelpProvider>
        <div className={navOpen ? "appshell appshell--nav-open" : "appshell"}>
        <a className="appshell__skip" href="#main">
          {t("shell.skipToContent")}
        </a>
        <Sidebar />
        <button
          type="button"
          className="appshell__overlay"
          aria-label={t("shell.closeMenu")}
          tabIndex={navOpen ? 0 : -1}
          onClick={() => setNavOpen(false)}
        />
        <CommandBar onMenu={() => setNavOpen((v) => !v)} />
        <main id="main" className="appshell__main" ref={mainRef}>
          {/* Re-keying on the path replays the enter animation each navigation,
              so pages glide in instead of snapping. */}
          <div key={location.pathname} className="appshell__content page-enter">
            {children}
          </div>
        </main>
        <HelpCenter />
        <Toaster />
      </div>
      </HelpProvider>
    </ToastProvider>
  );
}
