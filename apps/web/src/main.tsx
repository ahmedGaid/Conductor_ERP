import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";

// Self-hosted fonts (no cloud dependency). Declared with font-display: optional + preloaded in
// index.html so the brand font renders from first paint with no swap reflow — see styles/fonts.css.
import "./styles/fonts.css";

import "./styles/tokens.css";
import "./styles/global.css";
import "./styles/data-surfaces.css";
import "./styles/print.css";
import "./styles/module-accents.css";
import "./i18n";
import App from "./App";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root element #root not found");
}

createRoot(container).render(
  <StrictMode>
    <Suspense fallback={null}>
      <App />
    </Suspense>
  </StrictMode>,
);
