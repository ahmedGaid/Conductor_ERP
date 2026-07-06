// Client-side CSV for list pages (no backend export endpoint — rule 8 of the unified-ui plan).
// Report pages use the backend's own CSV/Excel (`downloadExport` in api/client.ts) instead.

export interface CsvColumn<T> {
  header: string;
  accessor: (row: T) => string | number;
}

function csvCell(value: string | number): string {
  const s = String(value ?? "");
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function rowsToCsv<T>(rows: T[], columns: CsvColumn<T>[]): string {
  const header = columns.map((c) => csvCell(c.header)).join(",");
  const lines = rows.map((row) => columns.map((c) => csvCell(c.accessor(row))).join(","));
  return [header, ...lines].join("\r\n");
}

// UTF-8 BOM so Arabic headers/cells open correctly in Excel rather than mojibake.
export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
