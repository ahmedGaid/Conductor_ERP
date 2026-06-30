import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { NavIcon } from "../app/icons";

/*
 * One back affordance for the whole app: a quiet, muted link with a single-stroke arrow that
 * points inline-start and mirrors correctly in RTL (the arrow is flipped by .backlink CSS).
 * Replaces the per-page hardcoded "←" glyph, which pointed the wrong way in the Arabic default.
 */
export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link className="backlink" to={to}>
      <NavIcon name="arrowBack" />
      <span>{children}</span>
    </Link>
  );
}
