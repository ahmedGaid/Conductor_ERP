import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180,
    proxy: {
      "/api": "http://127.0.0.1:8010",
      "/health": "http://127.0.0.1:8010",
      "/system-check": "http://127.0.0.1:8010",
    },
  },
  build: { outDir: "dist", sourcemap: true },
});
