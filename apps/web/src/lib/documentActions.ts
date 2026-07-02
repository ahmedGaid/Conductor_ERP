// Shared client-side actions for a document detail page (Print / Export PDF / Share). These need no
// backend: Print and Export PDF both use the browser print path (print.css strips the chrome; the
// user picks a printer or "Save as PDF"), and Share copies a canonical deep link to the clipboard.

/**
 * Open the browser print dialog for the current page. `filename` is set as the document title first
 * so a "Save as PDF" gets a sensible default name (e.g. the order number), then restored afterwards.
 */
export function printDocument(filename?: string): void {
  if (!filename) {
    window.print();
    return;
  }
  const previous = document.title;
  document.title = filename;
  const restore = () => {
    document.title = previous;
    window.removeEventListener("afterprint", restore);
  };
  window.addEventListener("afterprint", restore);
  window.print();
}

/**
 * Copy a shareable link to a record to the clipboard. `path` is an in-app route (e.g.
 * `/go/sales_order/SO-2026-000007`); it is turned into a full hash-router URL. Resolves to true on
 * success, false when the clipboard is unavailable.
 */
export async function copyShareLink(path: string): Promise<boolean> {
  const url = `${window.location.origin}/#${path}`;
  try {
    await navigator.clipboard.writeText(url);
    return true;
  } catch {
    return false;
  }
}
