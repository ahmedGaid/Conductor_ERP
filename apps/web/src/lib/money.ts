// Money on the frontend mirrors the backend: integer minor units, never a float for storage.
// These helpers only format for display and parse user input at the edge.

const MINOR = 100; // 2 minor digits (EGP)

/** Organization's base ERP currency — the one place this is ever spelled out as a literal. */
export const BASE_CURRENCY = "EGP";

/** 100000 -> "1,000.00" — numeral only, no currency (for table cells where currency lives in header). */
export function formatMoneyNumeral(minor: number): string {
  const sign = minor < 0 ? "-" : "";
  const abs = Math.abs(minor);
  const whole = Math.floor(abs / MINOR);
  const frac = abs % MINOR;
  return `${sign}${whole.toLocaleString("en-US")}.${String(frac).padStart(2, "0")}`;
}

/** 100000 -> "1,000.00 EGP" (display only; use formatMoneyNumeral in tables). */
export function formatMinor(minor: number, currency = BASE_CURRENCY): string {
  return `${formatMoneyNumeral(minor)} ${currency}`;
}

/**
 * AI provider cost: microcents (1e-6 of a USD cent) -> "$1,234.5678". Providers bill in USD with
 * no FX rate on file, so this is a distinct unit from the ERP's own EGP minor units above — not a
 * formatMinor variant. 4dp (not 2) because a single call often costs a fraction of one cent.
 */
export function formatMicrocentsUsd(microcents: number): string {
  const sign = microcents < 0 ? "-" : "";
  const dollars = Math.abs(microcents) / 100_000_000;
  return `${sign}$${dollars.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}`;
}

/** 200.0000 -> "200" for whole units, "1.50" for fractional; max 3 decimals (storage precision). */
export function formatQuantity(quantity: number): string {
  if (quantity === 0) return "0";
  const sign = quantity < 0 ? "-" : "";
  const abs = Math.abs(quantity);
  const integral = Math.trunc(abs);
  const frac = abs - integral;
  if (frac < 0.0001) return `${sign}${integral}`;
  return `${sign}${abs.toLocaleString("en-US", { maximumFractionDigits: 3 })}`;
}

/** 100050 -> "1000.50" — a plain amount string for a text input (no grouping/currency). */
export function minorToAmount(minor: number): string {
  return (minor / MINOR).toFixed(2);
}

/** "1000.50" -> 100050 minor units; returns null if the input is not a valid amount. */
export function parseToMinor(input: string): number | null {
  const t = input.trim();
  if (t === "") return 0;
  if (!/^-?\d+(\.\d{1,2})?$/.test(t)) return null;
  const neg = t.startsWith("-");
  const [w, f = ""] = t.replace("-", "").split(".");
  const frac = (f + "00").slice(0, 2);
  const minor = parseInt(w, 10) * MINOR + parseInt(frac, 10);
  return neg ? -minor : minor;
}
