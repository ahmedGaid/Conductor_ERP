import { useTranslation } from "react-i18next";

import { Bdi } from "./Bdi";
import { NavIcon } from "../app/icons";
import "./StatCard.css";

interface Props {
  label: string;
  value: string;
  icon?: string;
  delta?: number | null;
  hint?: string;
  /** When true, a positive delta is bad (e.g. expenses) and shown red. */
  invertDelta?: boolean;
  /** When true, the value itself is an alarming number (e.g. negative cash) — coloured + iconed + worded, not just a minus sign. */
  negative?: boolean;
  /** When set (with `negative`), the hint becomes a button that scrolls the named element id into view. */
  onHintClick?: () => void;
}

export function StatCard({ label, value, icon, delta, hint, invertDelta, negative, onHintClick }: Props) {
  const { t } = useTranslation();
  const hasDelta = delta !== undefined && delta !== null;
  const good = hasDelta ? (invertDelta ? (delta as number) < 0 : (delta as number) >= 0) : false;
  const trendWord = hasDelta ? t(good ? "dashboard.deltaUp" : "dashboard.deltaDown") : undefined;
  const hintText = negative ? t("dashboard.cashNegative") : (hint ?? t("dashboard.vsLastMonth"));
  const ariaLabel = [
    label,
    value,
    hasDelta ? `${Math.abs(delta as number)}% ${trendWord}` : null,
    hintText,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <div className="statcard" role="group" aria-label={ariaLabel}>
      <div className="statcard__top">
        <span className="statcard__label" aria-hidden="true">{label}</span>
        {icon && (
          <span className={negative ? "statcard__icon statcard__icon--negative" : "statcard__icon"} aria-hidden="true">
            <NavIcon name={negative ? "warning" : icon} />
          </span>
        )}
      </div>
      <div className={negative ? "statcard__value statcard__value--negative" : "statcard__value"} aria-hidden="true">
        <Bdi>{value}</Bdi>
      </div>
      <div className="statcard__foot" aria-hidden="true">
        {hasDelta ? (
          <span className={good ? "statcard__delta statcard__delta--up" : "statcard__delta statcard__delta--down"}>
            <NavIcon name={good ? "trendUp" : "trendDown"} />
            <Bdi>{Math.abs(delta as number)}%</Bdi>
          </span>
        ) : null}
        {negative && onHintClick ? (
          <button type="button" className="statcard__hint statcard__hint--negative statcard__hint--link" onClick={onHintClick}>
            {hintText}
          </button>
        ) : (
          <span className={negative ? "statcard__hint statcard__hint--negative" : "statcard__hint"}>{hintText}</span>
        )}
      </div>
    </div>
  );
}
