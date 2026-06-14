import { useTranslation } from "react-i18next";

import type { InstanceStatus } from "../api/types";
import "./StatusPill.css";

export function StatusPill({ status }: { status: InstanceStatus }) {
  const { t } = useTranslation();
  return (
    <span className={`pill pill--${status}`} data-status={status}>
      {t(`status.${status}`)}
    </span>
  );
}
