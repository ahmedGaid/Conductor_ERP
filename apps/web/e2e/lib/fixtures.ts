import { test as base, devices, type BrowserContext, type Page } from "@playwright/test";

import { tFor, type Locale } from "./i18n";
import { freshAccessToken, apiGet as rawApiGet, apiPost as rawApiPost, type ApiGet, type ApiPost } from "./api";

interface WorkerFixtures {
  appLocale: Locale;
  /** One authenticated browser context per worker (== per project, since workers:1) — see below. */
  authContext: BrowserContext;
  /** One access token per worker, minted once (see below) and reused by apiGet/apiPost. */
  apiToken: string;
}

interface TestFixtures {
  page: Page;
  t: (path: string) => string;
  /** Signed-in admin API calls, sharing the worker's one authenticated context (see below). */
  apiGet: ApiGet;
  apiPost: ApiPost;
}

// The backend rotates AND blacklists refresh tokens on use (SimpleJWT ROTATE_REFRESH_TOKENS +
// BLACKLIST_AFTER_ROTATION — config/settings/base.py). The app's own AuthContext calls the
// refresh endpoint once per fresh page boot (its in-memory access token resets per page/tab even
// though a browser CONTEXT's cookies persist), so a saved storageState's refresh cookie is
// single-use: the first test-scoped context to load it consumes it, and a fresh context per test
// would blacklist itself out by the second test. So the authenticated context is scoped to the
// WORKER, not the test — one browser context per locale, alive for the whole run, so that chain
// just keeps rotating forward instead of restarting from the same stale cookie every time. (Named
// `authContext` / `appLocale`, not `context` / `locale`, because those names are already
// Playwright built-ins fixed at test scope — a same-named override can't change scope.)
export const test = base.extend<TestFixtures, WorkerFixtures>({
  appLocale: [
    async ({}, use, workerInfo) => {
      await use(workerInfo.project.name === "en" ? "en" : "ar");
    },
    { scope: "worker" },
  ],

  authContext: [
    async ({ browser, appLocale }, use) => {
      const ctx = await browser.newContext({
        ...devices["Desktop Chrome"],
        storageState: `.auth/${appLocale}.json`,
      });
      await use(ctx);
      await ctx.close();
    },
    { scope: "worker" },
  ],

  // Minted via a plain login (not the refresh cookie — a second, independent refresh racing the
  // page's own boot-time refresh on that single-use cookie caused sporadic "Token is blacklisted"
  // failures in practice) and cached for the WORKER's whole run, not re-minted per apiGet/apiPost
  // call: logging in on every call, itself, sets a fresh `erp_refresh` Set-Cookie on this SAME
  // shared context every time (login and the page's own cookie-based refresh both write the one
  // `erp_refresh` cookie name) — frequent enough (e.g. inside a `toPass()` poll loop) it could
  // race a concurrent page reload's own refresh and knock the page back to the login screen.
  apiToken: [
    async ({ authContext, appLocale }, use) => {
      const token = await freshAccessToken(authContext.request);
      // The setup projects (setup-ar/setup-en) share ONE seeded admin account, so whichever ran
      // LAST leaves its language choice in that account's server-side preference — the ar and en
      // WORKERS would otherwise fight over it. Re-assert it here, once per worker, right before
      // this worker's own tests run, regardless of what the other project's setup did.
      const res = await authContext.request.patch("/api/identity/preferences", {
        data: { preferred_language: appLocale },
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok()) throw new Error(`set language preference failed: ${res.status()} ${await res.text()}`);
      await use(token);
    },
    { scope: "worker" },
  ],

  // Depends on apiToken (even though it isn't used directly) so that fixture's language-preference
  // side effect always runs before a test's first page interaction — regardless of whether that
  // particular test happens to destructure apiGet/apiPost/apiToken itself.
  page: async ({ authContext, apiToken: _apiToken }, use) => {
    const page = await authContext.newPage();
    await use(page);
    await page.close();
  },

  t: async ({ appLocale }, use) => {
    await use(tFor(appLocale));
  },

  apiGet: async ({ authContext, apiToken }, use) => {
    await use((path) => rawApiGet(authContext.request, path, apiToken));
  },

  apiPost: async ({ authContext, apiToken }, use) => {
    await use((path, body) => rawApiPost(authContext.request, path, body, apiToken));
  },
});

export { expect } from "@playwright/test";
