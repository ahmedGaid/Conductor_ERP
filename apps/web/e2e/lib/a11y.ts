import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

// Known, ALREADY-MITIGATED contrast gap, not fixed here: the default theme's `--color-text-subtle`
// tier sits under 4.5:1 (2.53:1) on purpose — a deliberately near-decorative faint tier — and the
// app already ships an opt-in escape hatch for it (Settings → Accessibility, `data-contrast="high"`
// in tokens.css, which darkens exactly this token). Re-litigating the default's darkness is a
// brand/product call, not an a11y-CI fix — flagged in DECISIONS.md ("a11y check" entry) for the
// founder, not silently changed here. (`--color-text-muted`, the OTHER de-emphasis tier, WAS fixed
// outright — see the same DECISIONS entry — since it's meant to be comfortably readable, not faint.)
const KNOWN_CONTRAST_GAPS = [".sidebar__group-label", ".commandbar__kbd", ".combobox-trigger__value--placeholder"];

/**
 * Scans the current page and fails on `serious`/`critical` axe violations only — `moderate`/
 * `minor` are deferred (see FILE_06 "Watch": a strict zero-violations bar would likely trip on
 * pre-existing lower-priority issues out of scope for this pass).
 */
export async function expectNoSeriousA11yViolations(page: Page): Promise<void> {
  const builder = new AxeBuilder({ page });
  for (const selector of KNOWN_CONTRAST_GAPS) builder.exclude(selector);
  const results = await builder.analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");

  if (serious.length > 0) {
    const report = serious
      .map((v) => {
        const targets = v.nodes.map((n) => n.target.join(" ")).join(", ");
        return `[${v.impact}] ${v.id}: ${v.help} — ${targets} (${v.helpUrl})`;
      })
      .join("\n");
    expect(serious, `serious/critical a11y violations:\n${report}`).toEqual([]);
  }
}
