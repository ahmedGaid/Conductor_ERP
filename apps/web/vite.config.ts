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
      // NOTE: "localhost" can resolve to ::1 first on this machine; use 127.0.0.1 explicitly
      // to avoid hitting whatever else is squatting the IPv6 side of port 8000.
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/system-check": "http://127.0.0.1:8000",
    },
  },
  // `vite preview` (production-build smoke test) needs its own proxy — server.proxy is dev-only.
  preview: {
    port: 4173,
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/system-check": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
    // Off deliberately: WhiteNoise serves everything in dist/ verbatim (WHITENOISE_ROOT, see
    // config/settings/prod.py), so a shipped .map hands the full unminified source to anyone
    // who can reach the site — and on the public demo that is anyone with the link. The maps
    // also dwarfed the bundle they described (1.7 MB map for a 780 kB chunk). Debug a
    // production stack trace by rebuilding locally with `sourcemap: true`, not by serving it.
    sourcemap: false,
  },
});
