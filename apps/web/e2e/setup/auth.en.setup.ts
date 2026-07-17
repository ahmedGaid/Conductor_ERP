import { test as setup } from "@playwright/test";

import { loginAndSaveState } from "../lib/login";

setup("authenticate (en)", async ({ page }) => {
  await loginAndSaveState(page, ".auth/en.json");
});
