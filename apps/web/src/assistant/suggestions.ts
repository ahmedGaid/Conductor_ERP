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

/** The i18n keys for the first-run empty-state chips (all four primary questions). */
export function firstRunSuggestions(): SuggestionKey[] {
  return [...SUGGESTION_KEYS];
}

/** Follow-up suggestion keys for the tool that just answered; empty when no tool fits. */
export function followupsFor(usedTool: string | null | undefined): SuggestionKey[] {
  if (!usedTool) return [];
  return FOLLOWUPS[usedTool] ?? [];
}
