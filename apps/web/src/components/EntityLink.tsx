import { Link } from "react-router-dom";
import type { ReactNode } from "react";

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

export function EntityLink({
  type,
  value,
  children,
  className,
}: {
  type: EntityType;
  /** The business key (code / sku / order number). Empty ⇒ render children as plain text. */
  value: string;
  children?: ReactNode;
  className?: string;
}) {
  if (!value) return <>{children ?? null}</>;
  return (
    <Link to={pathFor(type, value)} className={className}>
      {children ?? <Bdi>{value}</Bdi>}
    </Link>
  );
}
