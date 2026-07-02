import { useRef, useState } from "react";

import { Popover } from "./Popover";
import { NavIcon } from "../app/icons";
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
