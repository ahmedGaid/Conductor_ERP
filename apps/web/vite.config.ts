import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Customer-hosted, single-tenant: build is a static bundle that Django can serve.
// No cloud-only dependencies — fonts are self-hosted via @fontsource.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Dev convenience: forward API calls to the Django backend.
      "/api": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
