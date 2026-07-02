import type { ReactNode } from "react";

import { EntityLink } from "./EntityLink";

// A customer/supplier rendered as a link to its party page (transactions + ledger). Thin wrapper
// over the general EntityLink so party drill-downs stay consistent with every other entity mention.
export type PartyType = "customer" | "supplier";

export function PartyLink({
  type,
  code,
  children,
  className,
}: {
  type: PartyType;
  code: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <EntityLink type={type} value={code} className={className}>
      {children}
    </EntityLink>
  );
}
