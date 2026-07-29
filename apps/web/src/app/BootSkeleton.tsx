// The app frame as a placeholder — Conductor's shape before Conductor is ready.
//
// Used as the root <Suspense> fallback in main.tsx. That fallback used to be `null`, which meant
// a suspending lazy route or an in-flight i18n catalog painted a blank white page — a bare state,
// and indistinguishable from a broken build. This renders the same markup index.html inlines for
// the pre-React window, so the frame stays put from the first paint until the app takes over.
//
// Styling lives with the other skeleton rules in src/styles/global.css (.boot-skeleton*). Keep the
// markup here and the copy in index.html in step.
//
// Deliberately wordless: index.html is served before the language is known, and a "Loading…" that
// guessed wrong would be worse than the frame, which reads the same in Arabic and English.
const NAV_ITEMS = 6;
const BODY_ROWS = 4;

export function BootSkeleton() {
  return (
    <div className="boot-skeleton" aria-hidden="true">
      <div className="boot-skeleton__sidebar">
        {Array.from({ length: NAV_ITEMS }, (_, i) => (
          <span key={i} className="skeleton boot-skeleton__nav-item" />
        ))}
      </div>
      <div className="boot-skeleton__main">
        <div className="boot-skeleton__topbar">
          <span className="skeleton skeleton--title" />
        </div>
        <div className="boot-skeleton__body">
          {Array.from({ length: BODY_ROWS }, (_, i) => (
            <span key={i} className="skeleton skeleton--row" />
          ))}
        </div>
      </div>
    </div>
  );
}
