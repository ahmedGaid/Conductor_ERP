import { defineConfig, devices } from "@playwright/test";

import { env } from "./lib/env";

// NO webServer autostart: the dev environment is `run-dev.ps1` (Django :8000 + Vite :5173), a
// documented prerequisite (see Docs/RUNBOOK.md "Regression run before every release" and
// twenty-harvest-plan/FILE_04_E2E_PLAYWRIGHT.md). Point E2E_BASE_URL at the WhiteNoise-served
// build (http://localhost:8000) to exercise a production build instead of the Vite dev server.
const baseURL = env("E2E_BASE_URL") ?? "http://localhost:5173";

export default defineConfig({
  testDir: ".",
  outputDir: "test-results",
  // purchasing.spec's full lifecycle (request -> approve -> convert -> receive -> bill -> two
  // payments), each step server-verified with its own reload, legitimately runs close to 30s —
  // observed timing out right at that boundary under load, not hanging.
  timeout: 60_000,
  expect: { timeout: 10_000 },
  // The suite drives a single shared dev database through the real API (no per-test isolation),
  // so tests run serially — parallel workers would race each other's order/customer numbering.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  // ar runs first (it's the product default — see src/i18n/index.ts fallbackLng): a regression
  // that only breaks Arabic/RTL is the one this suite most needs to catch.
  projects: [
    { name: "setup-ar", testMatch: /setup\/auth\.ar\.setup\.ts/ },
    {
      name: "ar",
      testDir: "./specs",
      dependencies: ["setup-ar"],
      use: { ...devices["Desktop Chrome"], storageState: ".auth/ar.json" },
    },
    { name: "setup-en", testMatch: /setup\/auth\.en\.setup\.ts/ },
    {
      name: "en",
      testDir: "./specs",
      dependencies: ["setup-en"],
      use: { ...devices["Desktop Chrome"], storageState: ".auth/en.json" },
    },
  ],
});
