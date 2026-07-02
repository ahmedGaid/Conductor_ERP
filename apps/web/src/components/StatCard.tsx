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
}

export function StatCard({ label, value, icon, delta, hint, invertDelta }: Props) {
  const { t } = useTranslation();
  const hasDelta = delta !== undefined && delta !== null;
  const good = hasDelta ? (invertDelta ? (delta as number) < 0 : (delta as number) >= 0) : false;

  return (
    <div className="statcard">
      <div className="statcard__top">
        <span className="statcard__label">{label}</span>
        {icon && (
          <span className="statcard__icon" aria-hidden="true">
            <NavIcon name={icon} />
          </span>
        )}
      </div>
      <div className="statcard__value">
        <Bdi>{value}</Bdi>
      </div>
      <div className="statcard__foot">
        {hasDelta ? (
          <span className={good ? "statcard__delta statcard__delta--up" : "statcard__delta statcard__delta--down"}>
            <span aria-hidden="true">{(delta as number) >= 0 ? "▲" : "▼"}</span>
            <Bdi>{Math.abs(delta as number)}%</Bdi>
          </span>
        ) : null}
        <span className="statcard__hint">{hint ?? t("dashboard.vsLastMonth")}</span>
      </div>
    </div>
  );
}
