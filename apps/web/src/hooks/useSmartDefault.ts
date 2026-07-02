import { useEffect, useRef } from "react";

import { getLastUsed } from "../lib/lastUsed";

/**
 * Seed a select's initial value once its options arrive: prefer the user's last-used pick (when it
 * still exists in the list), else the only option when there's exactly one. Runs at most once and
 * never overrides a value the user already set — so a new document opens pre-filled with the obvious
 * choice, but picking "—" afterwards stays sticky. The single-option fallback is opt-out (`single`)
 * because it makes sense for warehouse/tax but not for the customer.
 */
export function useSmartDefault(
  options: readonly { code: string }[] | null | undefined,
  storageKey: string,
  current: string,
  set: (value: string) => void,
  { single = true }: { single?: boolean } = {},
): void {
  const seeded = useRef(false);
  useEffect(() => {
    if (seeded.current || !options || current) return;
    seeded.current = true;
    const last = getLastUsed(storageKey);
    if (last && options.some((o) => o.code === last)) set(last);
    else if (single && options.length === 1) set(options[0].code);
    // Seed once when options land; deliberately not re-running on `current`/`set` changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options]);
}
