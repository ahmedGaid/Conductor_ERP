import type { ReactNode } from "react";

/*
 * Sidebar nav icons — clean single-stroke line icons (ChatGPT/Lucide style):
 * 24×24 view box, `currentColor` stroke, rounded caps/joins, one consistent weight.
 * They inherit colour from the nav link (muted → text on hover/active), so the
 * sidebar reads as one calm, modern set rather than a row of mismatched glyphs.
 *
 * Direction-agnostic by construction (no left/right baked in) — works in RTL + LTR.
 */
const PATHS: Record<string, ReactNode> = {
  // Dashboard — 2×2 rounded grid.
  dashboard: (
    <>
      <rect x="3" y="3" width="7.5" height="7.5" rx="2" />
      <rect x="13.5" y="3" width="7.5" height="7.5" rx="2" />
      <rect x="3" y="13.5" width="7.5" height="7.5" rx="2" />
      <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2" />
    </>
  ),
  // Sales — shopping bag.
  sales: (
    <>
      <path d="M6 2 3.5 6.5V20a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2V6.5L18 2Z" />
      <path d="M3.5 6.5h17" />
      <path d="M16 10.5a4 4 0 0 1-8 0" />
    </>
  ),
  // Purchasing — package / inbound box.
  purchasing: (
    <>
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
      <path d="M3.3 7 12 12l8.7-5" />
      <path d="M12 22V12" />
    </>
  ),
  // Inventory — stacked layers.
  inventory: (
    <>
      <path d="M12 3 3 7.5l9 4.5 9-4.5L12 3Z" />
      <path d="M3 12l9 4.5 9-4.5" />
      <path d="M3 16.5l9 4.5 9-4.5" />
    </>
  ),
  // Accounting — bank / landmark.
  accounting: (
    <>
      <path d="M12 3 2.5 8h19L12 3Z" />
      <path d="M5 11v7" />
      <path d="M9.5 11v7" />
      <path d="M14.5 11v7" />
      <path d="M19 11v7" />
      <path d="M3 21h18" />
    </>
  ),
  // Pricing — price tag.
  pricing: (
    <>
      <path d="M3 7.5V4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 .7.3l11 11a1 1 0 0 1 0 1.4l-3.5 3.5a1 1 0 0 1-1.4 0l-11-11a1 1 0 0 1-.3-.7Z" />
      <circle cx="7" cy="7" r="1.1" />
    </>
  ),
  // E-invoicing — document with lines.
  einvoice: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
      <path d="M8.5 13h7" />
      <path d="M8.5 17h7" />
    </>
  ),
  // CRM — people.
  crm: (
    <>
      <path d="M16 21v-1.5a4 4 0 0 0-4-4H6.5a4 4 0 0 0-4 4V21" />
      <circle cx="9.25" cy="7.5" r="3.5" />
      <path d="M21.5 21v-1.5a4 4 0 0 0-3-3.85" />
      <path d="M16.5 4a3.5 3.5 0 0 1 0 6.8" />
    </>
  ),
  // Workflows — connected nodes.
  workflows: (
    <>
      <circle cx="18" cy="5" r="2.5" />
      <circle cx="6" cy="12" r="2.5" />
      <circle cx="18" cy="19" r="2.5" />
      <path d="M8.4 13.4 15.6 17.6" />
      <path d="M15.6 6.4 8.4 10.6" />
    </>
  ),
  // Notifications — bell.
  notifications: (
    <>
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.7 21a2 2 0 0 1-3.4 0" />
    </>
  ),
  // Reports — bar chart.
  reports: (
    <>
      <path d="M3 3v18h18" />
      <path d="M18 17V9" />
      <path d="M13 17V5" />
      <path d="M8 17v-3" />
    </>
  ),
  // Sidebar toggle — panel with a rail divider. Direction-agnostic (reads the same in RTL/LTR).
  sidebar: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M9 4v16" />
    </>
  ),
  // Close — X.
  close: (
    <>
      <path d="M6 6 18 18" />
      <path d="M18 6 6 18" />
    </>
  ),
  // More — horizontal kebab (overflow menu trigger).
  more: (
    <>
      <circle cx="5" cy="12" r="1.1" />
      <circle cx="12" cy="12" r="1.1" />
      <circle cx="19" cy="12" r="1.1" />
    </>
  ),
  // Duplicate — overlapping sheets (copy).
  duplicate: (
    <>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </>
  ),
  // Print — printer.
  print: (
    <>
      <path d="M6 9V3h12v6" />
      <path d="M6 18H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2" />
      <rect x="6" y="14" width="12" height="8" rx="1" />
    </>
  ),
  // Download — export (arrow into tray).
  download: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5 5 5-5" />
      <path d="M12 15V3" />
    </>
  ),
  // Share — connected nodes.
  share: (
    <>
      <circle cx="18" cy="5" r="2.5" />
      <circle cx="6" cy="12" r="2.5" />
      <circle cx="18" cy="19" r="2.5" />
      <path d="M8.2 10.8 15.8 6.2" />
      <path d="M8.2 13.2 15.8 17.8" />
    </>
  ),
  // Trash — delete / cancel.
  trash: (
    <>
      <path d="M3 6h18" />
      <path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </>
  ),
  // Rotate — undo / record return (counter-clockwise arrow).
  rotate: (
    <>
      <path d="M3 3v5h5" />
      <path d="M3.5 8a8.5 8.5 0 1 1-1.5 4.8" />
    </>
  ),
  // Info — circled i (in-progress / informational note).
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </>
  ),
  // Check-circle — completed / success state.
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.5 2.5 5-5.5" />
    </>
  ),
  // Settings — gear.
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </>
  ),
};

export function NavIcon({ name }: { name: string }) {
  return (
    <svg
      className="navicon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name] ?? null}
    </svg>
  );
}
