// Money on the frontend mirrors the backend: integer minor units, never a float for storage.
// These helpers only format for display and parse user input at the edge.

const MINOR = 100; // 2 minor digits (EGP)

/** 100000 -> "1,000.00 EGP" (display only). */
export function formatMinor(minor: number, currency = "EGP"): string {
  const sign = minor < 0 ? "-" : "";
  const abs = Math.abs(minor);
  const whole = Math.floor(abs / MINOR);
  const frac = abs % MINOR;
  return `${sign}${whole.toLocaleString("en-US")}.${String(frac).padStart(2, "0")} ${currency}`;
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
