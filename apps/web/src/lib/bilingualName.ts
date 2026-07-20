/**
 * Reference records the user reads by name — chart-of-accounts nodes, cost centers, tax codes,
 * branches, departments, price lists — travel with BOTH names on the wire (`name` = canonical
 * English, `name_ar` = Arabic). The server never guesses a locale; the client picks by its own
 * active language, so switching AR↔EN re-labels instantly without a refetch.
 *
 * A blank `name_ar` falls back to `name` — a chart seeded before the Arabic names existed still
 * reads, it just reads in English. Mirrors `erp/core/naming.py` on the server.
 */

export interface BilingualName {
  name: string;
  name_ar?: string | null;
}

/** True when `lang` is Arabic in any region form ("ar", "ar-EG"). */
export function isArabic(lang: string | undefined): boolean {
  return (lang ?? "").toLowerCase().startsWith("ar");
}

/** The record's name in `lang`, falling back to the canonical name when the Arabic one is blank. */
export function localizedName(row: BilingualName, lang: string | undefined): string {
  if (isArabic(lang)) return row.name_ar?.trim() || row.name;
  return row.name;
}

/**
 * `code · name` — the label every account/cost-center picker shows. The code stays first in both
 * languages (it is the thing people type); bidi isolation is the caller's job via `<Bdi>`.
 */
export function codeAndName(row: BilingualName & { code: string }, lang: string | undefined): string {
  return `${row.code} · ${localizedName(row, lang)}`;
}

/**
 * Both names, for search and filtering — typing either script finds the row regardless of which
 * language the screen is currently in.
 */
export function searchableNames(row: BilingualName): string {
  return row.name_ar?.trim() ? `${row.name} ${row.name_ar}` : row.name;
}
