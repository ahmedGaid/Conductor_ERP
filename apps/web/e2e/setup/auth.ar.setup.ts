import { test as setup } from "@playwright/test";

import { loginAndSaveState } from "../lib/login";

setup("authenticate (ar)", async ({ page }) => {
  await loginAndSaveState(page, ".auth/ar.json");
});
