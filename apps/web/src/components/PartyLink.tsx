import { Link } from "react-router-dom";
import type { ReactNode } from "react";

// A customer/supplier rendered as a link to its party page (transactions + ledger). Used anywhere a
// party appears so the drill-down is consistent. Falls back to plain text when there's no code.
export type PartyType = "customer" | "supplier";

const BASE: Record<PartyType, string> = {
  customer: "/sales/customers",
  supplier: "/purchasing/suppliers",
};

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
  if (!code) return <>{children}</>;
  return (
    <Link to={`${BASE[type]}/${encodeURIComponent(code)}`} className={className}>
      {children ?? code}
    </Link>
  );
}
