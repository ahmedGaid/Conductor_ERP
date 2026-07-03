import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { getItem, getWarehouse } from "../api/inventory";
import { listCustomers } from "../api/sales";
import { listSuppliers } from "../api/purchasing";
import { prefetch } from "../lib/prefetch";
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
  if (!value) return <>{children ?? null}</>;
  const warm = PREFETCH[type];
  return (
    <Link
      to={pathFor(type, value)}
      className={className}
      onMouseEnter={warm && (() => warm(value))}
      onFocus={warm && (() => warm(value))}
      onClick={onClick}
    >
      {children ?? <Bdi>{value}</Bdi>}
    </Link>
  );
}
