import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { downloadExport } from "../api/client";
import { useSetPageActions } from "../app/PageActionsContext";
import { useToast } from "../app/ToastContext";
import { copyShareLink } from "../lib/documentActions";
import type { DocMenuItem } from "../components/DocumentMenu";

/**
 * Publishes a report page's split pattern into the sticky bar (unified-ui FILE_00 decision 1):
 * PDF/print is the one visible primary, CSV + Excel fold into ⋯. `path` is the report's API path
 * including any query string (filters/period) so the download matches the on-screen data — pass
 * null while the report hasn't loaded yet, which publishes nothing.
 */
export function useReportPageActions(path: string | null): void {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const location = useLocation();
  const route = `${location.pathname}${location.search}`;

  const primary = useMemo(() => {
    if (!path) return undefined;
    return (
      <button type="button" className="btn btn--primary" onClick={() => window.print()}>
        {t("export.pdf")}
      </button>
    );
  }, [path, t]);

  const menuItems = useMemo<DocMenuItem[]>(() => {
    if (!path) return [];
    const sep = path.includes("?") ? "&" : "?";
    const url = (fmt: string) => `${path}${sep}export=${fmt}&lang=${i18n.language}`;
    const download = (fmt: string) => () =>
      void downloadExport(url(fmt)).catch((err) =>
        toast.show(err instanceof Error ? err.message : String(err), "error"),
      );
    return [
      { key: "csv", label: t("export.csv"), icon: "download", onClick: download("csv") },
      { key: "excel", label: t("export.excel"), icon: "download", onClick: download("xlsx") },
      {
        key: "share",
        label: t("document.share"),
        icon: "share",
        onClick: () =>
          void copyShareLink(route).then((ok) =>
            toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
          ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, i18n.language, t, route]);

  useSetPageActions({ primary, menuItems });
}
