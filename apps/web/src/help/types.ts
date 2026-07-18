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

/** Live facts a page publishes about its own state, for the drawer's Live tab to react to.
 *  Deliberately a flat bag of primitives: the page knows nothing about help, it just states what
 *  is true right now ({ subCount: 0, hasFailed: true }), and the guide's predicates read it. */
export type HelpSignals = Record<string, string | number | boolean>;

/** A message shown at the top of the Live tab only while `when(signals)` holds — the "right now"
 *  thing, ahead of the static prose. Tone maps to the existing status vocabulary. */
export interface HelpAlert {
  when: (s: HelpSignals) => boolean;
  tone: "info" | "warn" | "success";
  title: L;
  body: L;
}

/** One step of a live checklist. `done(signals)` decides whether it's ticked (observed, never
 *  self-reported). `detail` is the bit-by-bit walkthrough for reaching it — shown expanded while
 *  this is the current step, so the user is led one micro-action at a time, then collapses once
 *  done. `hint` is a single reassuring line shown under a done step (what just happened / what's
 *  next), optional. */
export interface HelpChecklistStep {
  label: L;
  detail?: L[];
  hint?: L;
  done: (s: HelpSignals) => boolean;
}

/** A task whose steps tick themselves off as the user actually does them. `done` on the whole
 *  checklist (optional) is the celebration line shown when every step is complete. */
export interface HelpChecklist {
  name: L;
  steps: HelpChecklistStep[];
  doneMessage?: L;
}

/** The full guide for one page. Only `title`, `purpose`, and `howItWorks` are required so a guide
 *  can start small and grow; the gate only checks that every route HAS a guide, not its depth.
 *
 *  Everything above `alerts` is the Guide tab: static reference prose, the same on every visit.
 *  `alerts` + `checklist` are the Live tab, which reads what the page published via
 *  `useSetHelpSignals`. A guide with neither is Guide-only and the drawer hides the tab switch —
 *  so existing guides render exactly as before. */
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
  alerts?: HelpAlert[];
  checklist?: HelpChecklist;
}

/** One thing that can go wrong on a journey, and its blame-free fix — never "error", always the
 *  concrete next action ("re-enter the amount", not "invalid input"). */
export interface JourneyPitfall {
  problem: L;
  fix: L;
}

/** A cross-page, task-based walkthrough for the standalone User Guide (`/help/guide`) — distinct
 *  from a `HelpGuide`, which is one page's contextual reference. A journey follows the user's goal
 *  ("create your first invoice") across however many screens that takes, in plain numbered steps. */
export interface Journey {
  id: string;
  title: L;
  summary: L;
  steps: L[];
  pitfalls?: JourneyPitfall[];
  related?: HelpLink[];
}

/** One glossary entry. Mirrors Identity System §6.1 one-to-one — the term/definition pair a user
 *  looks up when they hit unfamiliar Arabic product vocabulary. */
export interface GlossaryEntry {
  term: L;
  desc: L;
}
