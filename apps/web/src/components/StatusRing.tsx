import type { BadgeTone } from "./Badge";
import { lifecycleFraction, type LifecycleDocType } from "../lib/lifecycle";
import "./metaCells.css";

// Ring geometry — a 24-grid SVG (the icon hand), hairline arc, r chosen to sit at a table row's
// cap height. Circumference is precomputed for the stroke-dasharray sweep.
const R = 9;
const CIRC = 2 * Math.PI * R;

/**
 * At-a-glance lifecycle ring — Linear's density, Conductor's quiet. The arc fills by lifecycle
 * STAGE (draft = a sliver, paid/closed = full), coloured with the SAME status token the word
 * already uses on the page. Off-line statuses (cancelled/rejected/lost) draw a hollow track only.
 *
 * Brand rule, enforced by the API: the ring NEVER renders without its status word beside it —
 * `label` is required, and the ring itself is `aria-hidden` (the word carries the meaning, colour
 * never stands alone). Pass the already-translated status word.
 */
export function StatusRing({
  docType,
  status,
  tone,
  label,
}: {
  docType: LifecycleDocType;
  status: string;
  tone: BadgeTone;
  label: string;
}) {
  const fraction = lifecycleFraction(docType, status);
  // A hair of arc even on a fresh draft so the ring never reads as "empty on the line".
  const dash = fraction == null ? 0 : Math.max(fraction, 0.02) * CIRC;

  return (
    <span className={`meta-ring meta-ring--${tone}`}>
      <svg className="meta-ring__svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <circle className="meta-ring__track" cx="12" cy="12" r={R} fill="none" />
        {fraction != null && (
          <circle
            className="meta-ring__arc"
            cx="12"
            cy="12"
            r={R}
            fill="none"
            strokeDasharray={`${dash} ${CIRC}`}
          />
        )}
      </svg>
      <span className="meta-ring__label">{label}</span>
    </span>
  );
}
