import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { listSuppliers, listPurchaseOrders } from "../../api/purchasing";
import { generalLedger } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { formatMinor } from "../../lib/money";
import { PartyDetailView, type PartyOrderRow } from "../../components/PartyDetailView";
import { PurchasingNav } from "./PurchasingNav";
import "../sales/sales.css";

// Accounts Payable — the supplier sub-ledger. Matches AP_ACCOUNT in erp/purchasing/services/orders.py.
const AP_ACCOUNT_CODE = "2000";

export function SupplierDetailPage() {
  const { t } = useTranslation();
  const { code = "" } = useParams();

  const { data: suppliers } = useAsync(listSuppliers, [], "purchasing:suppliers");
  const { data: orders, loading, error, reload } = useAsync(() => listPurchaseOrders(), [code]);
  const { data: ledger } = useAsync(
    () => generalLedger(AP_ACCOUNT_CODE, { partyType: "supplier", party: code }),
    [code],
  );

  const supplier = (suppliers ?? []).find((s) => s.code === code) ?? null;
  const mine = useMemo(
    () => (orders ?? []).filter((o) => o.supplier_code === code),
    [orders, code],
  );

  const name = supplier?.name ?? mine[0]?.supplier_name ?? code;
  const notFound = !!suppliers && !!orders && !supplier && mine.length === 0;

  const totalBilled = mine.reduce((sum, o) => sum + o.billed_minor, 0);
  const summary = [
    { label: t("party.ordersCount"), value: String(mine.length) },
    { label: t("party.totalBilled"), value: formatMinor(totalBilled) },
    { label: t("party.balance"), value: formatMinor(ledger?.closing_balance ?? 0) },
  ];

  const rows: PartyOrderRow[] = mine.map((o) => ({
    id: o.id,
    number: o.number,
    date: o.order_date,
    statusLabel: t(`purchasing.status.${o.status}`),
    total: formatMinor(o.subtotal_minor, o.currency),
    outstanding: formatMinor(o.outstanding_minor, o.currency),
    href: `/purchasing/orders/${o.id}`,
  }));

  return (
    <PartyDetailView
      nav={<PurchasingNav />}
      backHref="/purchasing/suppliers"
      backLabel={t("party.backToSuppliers")}
      code={code}
      name={name}
      typeLabel={t("party.supplier")}
      summary={summary}
      ordersTitle={t("party.ordersTitle")}
      orders={rows}
      ordersEmpty={t("party.noOrders")}
      ledger={ledger ?? null}
      ledgerTitle={t("party.statementTitle")}
      loading={loading}
      error={error}
      onRetry={reload}
      notFound={notFound}
    />
  );
}
