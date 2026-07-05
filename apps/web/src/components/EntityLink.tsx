import { Link } from "react-router-dom";
import { useRef, type ReactNode } from "react";

import { getItem, getWarehouse } from "../api/inventory";
import { listCustomers } from "../api/sales";
import { listSuppliers } from "../api/purchasing";
import { prefetch } from "../lib/prefetch";
import { isPeekable, usePeek } from "./PeekCard";
import { Bdi } from "./Bdi";

// A business entity (order, item, warehouse, party, journal) rendered as a link to its detail page,
// so any mention of a record anywhere is a click-through. Used wherever a code/number appears in a
// table or detail. Falls back to plain children when there's no value (mirrors PartyLink).
export type EntityType =
  | "customer"
  | "supplier"
  | "item"
  | "warehouse"
  | "salesOrder"
  | "purchaseOrder"
  | "journal";

// Types whose detail page is keyed by the business value itself → link straight there.
const DIRECT: Partial<Record<EntityType, string>> = {
  customer: "/sales/customers",
  supplier: "/purchasing/suppliers",
  item: "/inventory/items",
  warehouse: "/inventory/warehouses",
};

// Types whose detail page is UUID-keyed → go through the resolver redirect (/go/:type/:key), which
// turns the business number into the record's id (see app/ResolveRedirect.tsx + api/core.ts).
const RESOLVE_SLUG: Partial<Record<EntityType, string>> = {
  salesOrder: "sales_order",
  purchaseOrder: "purchase_order",
  journal: "journal",
};

function pathFor(type: EntityType, value: string): string {
  const base = DIRECT[type];
  if (base) return `${base}/${encodeURIComponent(value)}`;
  return `/go/${RESOLVE_SLUG[type]}/${encodeURIComponent(value)}`;
}

// Hover/focus warms the destination's cache key (lib/prefetch) so the detail paints from cache.
// Item/warehouse details fetch by the business key itself; customer/supplier details read the
// shared master list. UUID-resolved types (orders, journals) prefetch nothing — their id isn't
// known until the resolver redirect runs.
const PREFETCH: Partial<Record<EntityType, (value: string) => void>> = {
  item: (sku) => prefetch(`inventory:item:${sku}`, () => getItem(sku)),
  warehouse: (code) => prefetch(`inventory:warehouse:${code}`, () => getWarehouse(code)),
  customer: () => prefetch("sales:customers", listCustomers),
  supplier: () => prefetch("purchasing:suppliers", listSuppliers),
};

export function EntityLink({
  type,
  value,
  children,
  className,
  onClick,
}: {
  type: EntityType;
  /** The business key (code / sku / order number). Empty ⇒ render children as plain text. */
  value: string;
  children?: ReactNode;
  className?: string;
  /** Fired on navigation — e.g. to close a floating panel the link was clicked from. */
  onClick?: () => void;
}) {
  const peek = usePeek();
  // Delay before a steady hover shows the peek card — long enough that skimming past a link never
  // flashes one, short enough to feel instant on a deliberate pause.
  const hoverTimer = useRef<number | undefined>(undefined);

  if (!value) return <>{children ?? null}</>;
  const warm = PREFETCH[type];
  const canPeek = isPeekable(type);

  return (
    <Link
      to={pathFor(type, value)}
      className={className}
      // Pointer (mouse only) warms the cache and arms the peek; touch never peeks (a tap navigates).
      onPointerEnter={(e) => {
        if (e.pointerType !== "mouse") return;
        warm?.(value);
        if (!canPeek) return;
        const el = e.currentTarget;
        window.clearTimeout(hoverTimer.current);
        hoverTimer.current = window.setTimeout(() => peek.openPeek(type, value, el), 400);
      }}
      onPointerLeave={() => {
        window.clearTimeout(hoverTimer.current);
        if (canPeek) peek.scheduleClose();
      }}
      onFocus={warm && (() => warm(value))}
      onClick={() => {
        window.clearTimeout(hoverTimer.current);
        peek.closePeek();
        onClick?.();
      }}
      // Read by the list keyboard layer: `space` on the active row peeks its primary entity.
      data-peek-type={canPeek ? type : undefined}
      data-peek-value={canPeek ? value : undefined}
    >
      {children ?? <Bdi>{value}</Bdi>}
    </Link>
  );
}
