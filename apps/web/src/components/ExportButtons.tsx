import { useState } from "react";
import { useTranslation } from "react-i18next";

import { downloadExport } from "../api/client";
import "./ExportButtons.css";

/**
 * Export toolbar for a report screen. CSV/Excel download from the backend (`?format=…&lang=…`);
 * PDF is the browser's native print-to-PDF (perfect RTL, no fonts) via the print stylesheet.
 *
 * `path` is the report's API path including any existing query string, e.g.
 * `/accounting/reports/trial-balance?period=2026-06`.
 */
export function ExportButtons({ path }: { path: string }) {
  const { t, i18n } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const sep = path.includes("?") ? "&" : "?";
  const url = (fmt: string) => `${path}${sep}export=${fmt}&lang=${i18n.language}`;

  async function download(fmt: string) {
    setError(null);
    try {
      await downloadExport(url(fmt));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="export-buttons no-print">
      <button type="button" className="btn btn--sm" onClick={() => download("csv")}>
        {t("export.csv")}
      </button>
      <button type="button" className="btn btn--sm" onClick={() => download("xlsx")}>
        {t("export.excel")}
      </button>
      <button type="button" className="btn btn--sm" onClick={() => window.print()}>
        {t("export.pdf")}
      </button>
      {error && <span className="error-text">{error}</span>}
    </div>
  );
}
