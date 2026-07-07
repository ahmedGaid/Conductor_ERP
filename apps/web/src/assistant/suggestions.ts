// Curated follow-up questions offered after an answer. We map the data tool that answered to two
// sibling questions the assistant can also answer — deterministic, always route to a real tool (so
// a follow-up never dead-ends), and localised through i18n rather than model-translated. This keeps
// the follow-ups calm and trustworthy without a second, paid model call per message.
//
// The four keys reused here are the same first-run suggestion chips (assistant.suggestions.s1–s4),
// each of which already maps one-to-one onto a primary tool:
//   s1 = sales this month   s2 = top customers   s3 = who owes us   s4 = what's low in stock
const SUGGESTION_KEYS = ["s1", "s2", "s3", "s4"] as const;
export type SuggestionKey = (typeof SUGGESTION_KEYS)[number];

// used_tool -> up to three sibling suggestion keys (never the one just asked).
const FOLLOWUPS: Record<string, SuggestionKey[]> = {
  sales_summary: ["s2", "s3"],
  top_customers: ["s3", "s1"],
  overdue_receivables: ["s1", "s2"],
  find_orders: ["s1", "s2"],
  low_stock: ["s1", "s2"],
};

// Empty-state prompts keyed by module and record presence (plan session 11). Same discipline as
// the follow-ups: every chip resolves through a real tool (or a proposable draft action) — no
// aspirational chips. `record` sets lean on the page-record resolution rule ("this order" is the
// record the user is viewing); `bare` sets are the module's report questions.
const PAGE_SUGGEST: Record<string, { record: string[]; bare: string[] }> = {
  sales: { record: ["r1", "r2", "r3", "r4"], bare: ["b1", "b2", "b3", "b4"] },
  purchasing: { record: ["r1", "r2", "r3", "r4"], bare: ["b1", "b2", "b3", "b4"] },
  inventory: { record: ["r1", "r2", "r3", "r4"], bare: ["b1", "b2", "b3", "b4"] },
  accounting: { record: ["r1", "r2", "r3", "r4"], bare: ["b1", "b2", "b3", "b4"] },
  crm: { record: ["r1", "r2", "r3", "r4"], bare: ["b1", "b2", "b3", "b4"] },
};

/**
 * Full i18n keys for the empty-conversation chips: module-aware when the user is inside a module
 * (and record-aware on a detail page), the original four everywhere else (dashboard, settings…).
 */
export function suggestionKeys(module: string | null, hasRecord: boolean): string[] {
  const entry = module ? PAGE_SUGGEST[module] : undefined;
  if (!entry) return SUGGESTION_KEYS.map((k) => `assistant.suggestions.${k}`);
  const set = hasRecord ? entry.record : entry.bare;
  return set.map((k) => `assistant.pageSuggest.${module}.${hasRecord ? "record" : "bare"}.${k}`);
}

/** Follow-up suggestion keys for the tool that just answered; empty when no tool fits. */
export function followupsFor(usedTool: string | null | undefined): SuggestionKey[] {
  if (!usedTool) return [];
  return FOLLOWUPS[usedTool] ?? [];
}
