import { Navigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { resolveEntity } from "../api/core";
import { useAsync } from "../hooks/useAsync";
import { EmptyState } from "../components/EmptyState";
import { ListSkeleton } from "../components/ListSkeleton";

// Turns a business-key link (/go/:type/:key) into the record's UUID-keyed detail route. EntityLink
// builds these for documents whose detail page is keyed by id, so a mention can link by number alone.
const DEST: Record<string, (id: string) => string> = {
  sales_order: (id) => `/sales/orders/${id}`,
  purchase_order: (id) => `/purchasing/orders/${id}`,
  journal: (id) => `/accounting/journals/${id}`,
};

export function ResolveRedirect() {
  const { t } = useTranslation();
  const { type = "", key = "" } = useParams<{ type: string; key: string }>();
  const dest = DEST[type];
  const { data, loading } = useAsync(() => resolveEntity(type, key), [type, key]);

  if (!dest) return <Navigate replace to="/" />;
  if (data) return <Navigate replace to={dest(data.id)} />;
  if (loading) return <ListSkeleton />;
  // No match (or the lookup failed): a designed dead-end, not a blank, with a way back.
  return (
    <EmptyState
      title={t("resolve.notFoundTitle")}
      hint={t("resolve.notFound", { key })}
      action={{ label: t("resolve.backHome"), to: "/" }}
    />
  );
}
