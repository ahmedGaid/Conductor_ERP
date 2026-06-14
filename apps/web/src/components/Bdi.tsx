import type { ReactNode } from "react";

/**
 * Isolate a bidirectional run so LTR tokens (codes, numbers, emails, English
 * names) render correctly inside an RTL paragraph and vice-versa.
 */
export function Bdi({ children }: { children: ReactNode }) {
  return <bdi className="latin">{children}</bdi>;
}
