import type { Locator, Page } from "@playwright/test";

/**
 * Drives the ComboBox component (src/components/ComboBox.tsx) the way a user would: click the
 * `.combobox-trigger` button to open the popover, type into the search box to filter, then click
 * the matching `.popover__item`. Replaces `.selectOption()` on forms migrated off native <select>
 * per the field-primitives-standard rollout.
 *
 * @param trigger the ComboBox's own trigger locator (e.g. `page.getByLabel(...)` or
 *   `row.locator(".combobox-trigger")`) — NOT a page-scoped locator, so it works inside repeated
 *   table rows without ambiguity.
 * @param optionText the option's visible label (or a unique substring) to search + click.
 */
export async function pickCombo(page: Page, trigger: Locator, optionText: string): Promise<void> {
  await trigger.click();
  const popover = page.locator(".combobox-popover");
  await popover.locator(".popover__search").fill(optionText);
  await popover.locator(".popover__item", { hasText: optionText }).first().click();
}
