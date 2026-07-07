import { useTranslation } from "react-i18next";

import { Tooltip } from "./Tooltip";
import "./metaCells.css";

// Three ascending bars; filled count = level. Four priorities share three bars: `high` and
// `urgent` both fill all three, and `urgent` is set apart the on-brand way — the danger token PLUS
// the label word beside it (colour never stands alone). low/medium/high stay monochrome, their
// word carried by the tooltip.
const FILLED: Record<string, number> = { low: 1, medium: 2, high: 3, urgent: 3 };

/**
 * Priority meter for urgency-worked queues (tickets, leads). Reads at a glance; the exact level is
 * one hover away, and the only splash of colour — danger, on `urgent` — is always paired with its
 * word. Pass the raw priority; the component owns the lexicon lookup.
 */
export function PriorityBar({ priority }: { priority: string }) {
  const { t } = useTranslation();
  const filled = FILLED[priority] ?? 1;
  const urgent = priority === "urgent";
  const word = t(`crm.priority.${priority}`);

  return (
    <span className={`meta-priority${urgent ? " meta-priority--urgent" : ""}`}>
      <Tooltip label={word}>
        <span className="meta-priority__bars" aria-label={word}>
          {[0, 1, 2].map((i) => (
            <span key={i} className={`meta-priority__bar${i < filled ? " is-on" : ""}`} />
          ))}
        </span>
      </Tooltip>
      {urgent && <span className="meta-priority__word">{word}</span>}
    </span>
  );
}
