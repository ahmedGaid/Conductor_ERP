import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { HashLink } from "./HashLink";
import { LandingNav } from "./LandingNav";
import { HeroSection } from "./HeroSection";
import {
  BusinessProblemSection,
  CoreERPSection,
  AIContextSection,
  HumanControlSection,
  SimulationSection,
  SmartImportSection,
  EgyptSection,
  SecuritySection,
  BusinessSyncSection,
  FinalCTA,
} from "./StorySections";
import { PricingSection } from "./PricingSection";
import { LandingFooter } from "./LandingFooter";
import "./landing.css";

type LandingTheme = "light" | "dark";
const STORAGE_KEY = "erp.landing.theme";

/**
 * Public marketing landing (route: /welcome). Lives OUTSIDE the authenticated app shell, so it
 * carries its own nav/footer AND its own light/dark theme — independent of the visitor's in-app
 * theme. Light is the hero aesthetic (airy, Dia-class); a toggle flips to a committed dark variant
 * via the `.landing-dark` wrapper, which re-maps the dark colour tokens onto this subtree only
 * (see tokens.css), keeping every surface token-driven and RTL/LTR-correct.
 *
 * Slice 1: Nav · Hero · Pricing (with the interactive per-user builder) · Footer. The remaining
 * story sections land in follow-up slices between Hero and Pricing.
 */
export function LandingPage() {
  const { t } = useTranslation();
  const [theme, setTheme] = useState<LandingTheme>(() => {
    if (typeof localStorage === "undefined") return "light";
    return localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
  });

  useEffect(() => {
    const prev = document.title;
    document.title = t("landing.meta.title");
    return () => {
      document.title = prev;
    };
  }, [t]);

  const toggleTheme = () => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* storage blocked — the in-memory state still drives the toggle */
      }
      return next;
    });
  };

  return (
    <div className={`lp landing-${theme}`} data-lp-theme={theme}>
      <HashLink to="#top" className="lp-skip">
        {t("landing.nav.skip")}
      </HashLink>
      <LandingNav theme={theme} onToggleTheme={toggleTheme} />
      <main>
        <HeroSection />
        <BusinessProblemSection />
        <CoreERPSection />
        <AIContextSection />
        <HumanControlSection />
        <SimulationSection />
        <SmartImportSection />
        <EgyptSection />
        <SecuritySection />
        <BusinessSyncSection />
        <PricingSection />
        <FinalCTA />
      </main>
      <LandingFooter />
    </div>
  );
}

export default LandingPage;
