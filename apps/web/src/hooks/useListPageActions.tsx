import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { useSetPageActions } from "../app/PageActionsContext";
import { DocumentPrimaryButton, type DocumentPrimary } from "../components/DocumentHeader";
import type { DocMenuItem } from "../components/DocumentMenu";
import { rowsToCsv, downloadCsv, type CsvColumn } from "../lib/csvExport";

/**
 * Publishes a list page's "New" action as the bar primary, plus print + client CSV (of the current
 * filtered/visible rows) into ⋯ (unified-ui FILE_03). Lists have no backend export endpoint (rule
 * 8) — CSV is generated client-side; Excel is omitted (no xlsx dependency, rule 9) but CSV opens in
 * Excel fine. Pass a STABLE `primary` (wrap in useMemo at the call site) — it's an effect dep.
 */
export function useListPageActions<T>({
  primary,
  rows,
  columns,
  filename,
}: {
  primary?: DocumentPrimary;
  rows: T[] | null | undefined;
  columns: CsvColumn<T>[];
  filename: string;
}): void {
  const { t } = useTranslation();

  const primaryNode = useMemo(
    () => (primary ? <DocumentPrimaryButton action={primary} /> : undefined),
    [primary],
  );

  const menuItems = useMemo<DocMenuItem[]>(() => {
    if (!rows || rows.length === 0) return [];
    return [
      { key: "print", label: t("document.print"), icon: "print", onClick: () => window.print() },
      {
        key: "csv",
        label: t("export.csv"),
        icon: "download",
        onClick: () => downloadCsv(filename, rowsToCsv(rows, columns)),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, columns, filename, t]);

  useSetPageActions({ primary: primaryNode, menuItems });
}
