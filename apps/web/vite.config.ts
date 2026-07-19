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
    sourcemap: true,
  },
});
