import { useTranslation } from "react-i18next";

import type { InstanceStatus } from "../api/types";
import { Badge } from "./Badge";

// Workflow instance status chip. InstanceStatus is a subset of the Badge tones, so the
// status doubles as the tone.
export function StatusPill({ status }: { status: InstanceStatus }) {
  const { t } = useTranslation();
  return <Badge tone={status}>{t(`status.${status}`)}</Badge>;
}
