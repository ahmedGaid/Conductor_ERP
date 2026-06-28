import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { RouteBreadcrumb } from "./RouteBreadcrumb";
import { CommandBar } from "./CommandBar";
import { ShortcutsDialog } from "./ShortcutsDialog";
import { ShortcutsProvider, useShortcuts } from "./ShortcutsContext";
import { Toaster } from "./Toaster";
import { ToastProvider } from "./ToastContext";
import { HelpCenter } from "../help/HelpCenter";
import { HelpProvider } from "../help/HelpContext";
import { usePreferences } from "../preferences/PreferencesContext";
import "./AppShell.css";

// First path segment names the active module; exposed as data-module on the shell so
// the per-module accent (tokens.css) cascades to the page (links, tabs, bars). Only the
// modules with a defined accent qualify; everything else stays the global accent.
const MODULE_SET = new Set(["sales", "purchasing", "inventory", "accounting", "crm"]);
function moduleFromPath(pathname: string): string | undefined {
  const seg = pathname.split("/")[1];
  return MODULE_SET.has(seg) ? seg : undefined;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const location = useLocation();
  const activeModule = moduleFromPath(location.pathname);
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
        <ShortcutsProvider>
          <div
            className={navOpen ? "appshell appshell--nav-open" : "appshell"}
            data-module={activeModule}
          >
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
                <RouteBreadcrumb />
                {children}
              </div>
            </main>
            <HelpCenter />
            <ShortcutsHost />
            <Toaster />
          </div>
        </ShortcutsProvider>
      </HelpProvider>
    </ToastProvider>
  );
}

// One mounted cheat-sheet, driven by the shared context so the `?` key and the product menu both
// open the same dialog. Reads the e-invoicing flag so the shortcut list matches the live nav.
function ShortcutsHost() {
  const { open, closeShortcuts } = useShortcuts();
  const { prefs } = usePreferences();
  return (
    <ShortcutsDialog
      open={open}
      onClose={closeShortcuts}
      einvoiceEnabled={prefs?.einvoice_enabled !== false}
    />
  );
}
