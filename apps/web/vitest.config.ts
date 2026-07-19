import { defineConfig } from "vitest/config";

// Pure-logic unit tests only (money, validation, workflow-state) — no DOM rendering needed yet,
// so no jsdom environment / testing-library dependency (post-handover-v1_1 FILE_04). Kept as a
// separate config from vite.config.ts so `vitest`'s `test` field never touches the build config.
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
  },
});
