import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { recordRecent } from "../lib/recents";

/**
 * Register the current entity page in the ⌘K "Recent" list with a human label (an order number,
 * an opportunity title, …). Detail pages load their data asynchronously, so the label isn't known
 * at navigation time — call this once it is, and the recents entry is upgraded in place. A falsy
 * label is ignored (still loading), so we never record a placeholder.
 */
export function useRecentEntity(label: string | undefined | null): void {
  const { pathname } = useLocation();
  useEffect(() => {
    const trimmed = label?.trim();
    if (trimmed) recordRecent(pathname, trimmed);
  }, [pathname, label]);
}
