/**
 * The Conductor logo glyph, theme-aware. Both marks render; CSS shows the one that reads on the
 * current landing theme — the black glyph on light, the white glyph on dark (the `.landing-dark`
 * wrapper flips them). Transparent (no tile) for a clean, premium lockup. Decorative: the wordmark
 * beside it carries the accessible name.
 */
export function BrandMark({ className = "" }: { className?: string }) {
  return (
    <span className={`lp-mark ${className}`.trim()} aria-hidden="true">
      <img
        className="lp-mark__img lp-mark__img--light"
        src="/branding/conductor-dark-transparent.svg"
        alt=""
        width={512}
        height={512}
      />
      <img
        className="lp-mark__img lp-mark__img--dark"
        src="/branding/conductor-light-transparent.svg"
        alt=""
        width={512}
        height={512}
      />
    </span>
  );
}
