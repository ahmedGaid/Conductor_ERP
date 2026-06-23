/*
 * Arabic-aware search folding.
 *
 * Display text stays in full, correct Arabic orthography (أمر، فاتورة، مستودع…). But users
 * type quickly and inconsistently — without hamzas, with ه for ة, with either yaa form. So for
 * *matching only* (never for display) we fold both the query and the candidate text to one
 * canonical shape, so either spelling finds the other:
 *   "امر البيع"  ⇄  "أمر البيع"      (hamza on alef)
 *   "فاتوره"     ⇄  "فاتورة"          (taa marbuta / haa)
 *   "نهائى"      ⇄  "نهائي"           (alef-maqsura / yaa)
 *
 * Folding is intentionally aggressive (it collapses medial yaa too) because it is invisible —
 * it shapes the comparison key, not anything the user reads. Latin text is unaffected beyond the
 * caller's lower-casing.
 */

const TASHKEEL = /[ً-ْٰ]/g; // harakat, tanwin, shadda, sukun, dagger-alef
const TATWEEL = /ـ/g; // ـ kashida

/** Fold Arabic letter variants to a single search form. Apply to BOTH sides of a comparison. */
export function foldArabic(s: string): string {
  return s
    .replace(TASHKEEL, "")
    .replace(TATWEEL, "")
    .replace(/[أإآٱ]/g, "ا") // أ إ آ ٱ → ا
    .replace(/ؤ/g, "و") // ؤ → و
    .replace(/[ئي]/g, "ى") // ئ ي → ى
    .replace(/ة/g, "ه") // ة → ه
    .replace(/ء/g, ""); // bare hamza ء → drop
}

/** Canonical search key: lower-cased (Latin) + Arabic-folded. Use for query and candidate alike. */
export function normalizeSearch(s: string): string {
  return foldArabic(s.toLowerCase());
}

/** True when `needle` is contained in `haystack` under Arabic-insensitive, case-insensitive folding. */
export function searchIncludes(haystack: string, needle: string): boolean {
  return normalizeSearch(haystack).includes(normalizeSearch(needle));
}
