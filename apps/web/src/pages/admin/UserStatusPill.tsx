import { useTranslation } from "react-i18next";

// User lifecycle pill (active/invited/suspended/archived). Self-contained — the shared StatusPill is
// typed to workflow statuses, so user states get their own token-driven colours in admin.css.
export function UserStatusPill({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <span className={`upill upill--${status}`} data-status={status}>
      {t(`admin.status.${status}`)}
    </span>
  );
}
