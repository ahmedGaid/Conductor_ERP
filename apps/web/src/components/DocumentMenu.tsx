import { useRef, useState } from "react";
import type { TFunction } from "i18next";

import { Popover } from "./Popover";
import { NavIcon } from "../app/icons";
import type { ToastApi } from "../app/ToastContext";
import { copyShareLink, printDocument } from "../lib/documentActions";
import "./documentMenu.css";

export interface DocMenuItem {
  key: string;
  label: string;
  /** Icon name from the app icon set (src/app/icons.tsx). */
  icon?: string;
  onClick: () => void;
  /** Destructive item (e.g. Cancel Order) — rendered in the danger colour. */
  danger?: boolean;
  disabled?: boolean;
  /** Required role name (from `useAuth().roles`), if any — absent, not greyed, when lacking it. */
  permission?: string;
}

/**
 * Drops items the current user lacks the permission for — quiet, not greyed (FILE_00 decision 4).
 * Items without a `permission` always pass. `hasRole` is `useAuth().hasRole`.
 */
export function filterMenuItems(items: DocMenuItem[], hasRole: (role: string) => boolean): DocMenuItem[] {
  return items.filter((item) => !item.permission || hasRole(item.permission));
}

export interface DocumentBaseMenuOptions {
  t: TFunction;
  /** Document number — sets the Print / Export-PDF filename. */
  number: string;
  /** In-app deep link for Share (e.g. `/sales/quotations/12`, `/go/sales_order/SO-…`). */
  sharePath: string;
  toast: ToastApi;
  onDuplicate: () => void;
  /** Override Export-PDF (defaults to the browser print of `number`, same as Print). */
  onExportPdf?: () => void;
}

/**
 * The four actions every document detail page shares — Duplicate · Print · Export PDF · Share —
 * built once so they read and behave identically on every order, quotation, PO and request. Pages
 * spread the result, then push their own lifecycle items (Submit, Convert, Cancel, …) after it.
 */
export function documentBaseMenu({
  t,
  number,
  sharePath,
  toast,
  onDuplicate,
  onExportPdf,
}: DocumentBaseMenuOptions): DocMenuItem[] {
  return [
    { key: "duplicate", label: t("document.duplicate"), icon: "duplicate", onClick: onDuplicate },
    { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(number) },
    {
      key: "pdf",
      label: t("document.exportPdf"),
      icon: "download",
      onClick: onExportPdf ?? (() => printDocument(number)),
    },
    {
      key: "share",
      label: t("document.share"),
      icon: "share",
      onClick: () =>
        void copyShareLink(sharePath).then((ok) =>
          toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
        ),
    },
  ];
}

/**
 * The ⋯ overflow menu for a document detail page (Duplicate / Print / Export PDF / Share / Cancel).
 * A monochrome icon trigger that opens the shared Popover; colour only reaches a destructive item.
 * Each item closes the menu before acting, so a navigation or dialog isn't fighting the open panel.
 */
export function DocumentMenu({ items, ariaLabel }: { items: DocMenuItem[]; ariaLabel: string }) {
  const anchorRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);

  if (items.length === 0) return null;

  return (
    <>
      <button
        ref={anchorRef}
        type="button"
        className="btn btn--icon"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((o) => !o)}
      >
        <NavIcon name="more" />
      </button>
      <Popover open={open} onClose={() => setOpen(false)} anchorRef={anchorRef} className="doc-menu" ariaLabel={ariaLabel}>
        <div className="popover__menu doc-menu__list" role="menu">
          {items.map((it) => (
            <button
              key={it.key}
              type="button"
              role="menuitem"
              className={`popover__item doc-menu__item${it.danger ? " doc-menu__item--danger" : ""}`}
              disabled={it.disabled}
              onClick={() => {
                setOpen(false);
                it.onClick();
              }}
            >
              {it.icon && <NavIcon name={it.icon} />}
              <span>{it.label}</span>
            </button>
          ))}
        </div>
      </Popover>
    </>
  );
}
