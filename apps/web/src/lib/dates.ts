// Period helpers — periods are coded "YYYY-MM" (see seed_accounting).

export function periodCode(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function currentPeriod(): string {
  return periodCode(new Date());
}

export function previousPeriod(): string {
  const d = new Date();
  d.setMonth(d.getMonth() - 1);
  return periodCode(d);
}

/** Percentage change current vs previous, rounded to 1 decimal; null when no baseline. */
export function pctChange(current: number, previous: number): number | null {
  if (previous === 0) return null;
  return Math.round(((current - previous) / Math.abs(previous)) * 1000) / 10;
}
