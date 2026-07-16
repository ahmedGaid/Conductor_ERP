import type { Page } from "@playwright/test";

import { env } from "./env";

// Seeded admin login (see run-dev.ps1 / erp-status skill) — never hard-coded, so CI or a
// differently-seeded box can override via env.
const USERNAME = env("E2E_ADMIN_USERNAME") ?? "admin";
const PASSWORD = env("E2E_ADMIN_PASSWORD") ?? "Dev12345!";

/**
 * Log in as the seeded admin and save the authenticated storage state to `path` for the matching
 * project to reuse. (The UI language is asserted separately, per-worker, in lib/fixtures.ts —
 * `PreferencesContext` re-applies the signed-in user's SERVER-side language preference on every
 * mount, which would silently override anything set only here at setup time.)
 */
export async function loginAndSaveState(page: Page, path: string): Promise<void> {
  await page.goto("/#/login");

  // Selectors keyed off `autocomplete`, not label text — LoginPage sets these regardless of
  // language, so this helper works identically for both locales.
  await page.locator('input[autocomplete="username"]').fill(USERNAME);
  await page.locator('input[autocomplete="current-password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();

  // A successful login navigates away from #/login (to the dashboard or the user's landing page).
  await page.waitForURL((url) => !url.hash.includes("/login"), { timeout: 15_000 });
  await page.context().storageState({ path });
}
