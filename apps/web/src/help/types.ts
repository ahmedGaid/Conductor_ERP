// Context-sensitive help content model.
//
// Every page has one HelpGuide, authored in both languages (the app is Arabic/RTL-first, so a
// guide that existed only in English would be useless to most users). The drawer picks the right
// language at render time from the active i18n locale. Guide content lives in plain TS modules
// (not the i18n JSON) so authors can write long-form prose without bloating the parity-checked
// locale files — the drawer's chrome labels (the only short, repeated strings) are the i18n keys.

/** A bilingual string. Author both; the drawer shows the active language. */
export type L = { en: string; ar: string };

/** A named thing on the page — a field, a button, a column, a status — and what it means/does. */
export interface HelpItem {
  term: L;
  desc: L;
}

/** A described region of the page (a form, a table, a toolbar) with optional itemised parts. */
export interface HelpSection {
  heading: L;
  body?: L;
  items?: HelpItem[];
}

/** A common task the user comes to this page to do, broken into ordered, plain-language steps. */
export interface HelpTask {
  name: L;
  steps: L[];
}

/** A pointer to a related page (route path) the user might need next. */
export interface HelpLink {
  to: string;
  label: L;
}

/** The full guide for one page. Only `title`, `purpose`, and `howItWorks` are required so a guide
 *  can start small and grow; the gate only checks that every route HAS a guide, not its depth. */
export interface HelpGuide {
  title: L;
  purpose: L;
  howItWorks: L;
  sections?: HelpSection[];
  tasks?: HelpTask[];
  examples?: L[];
  tips?: L[];
  mistakes?: L[];
  related?: HelpLink[];
}
