import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { listSuppliers, listPurchaseOrders } from "../../api/purchasing";
import { generalLedger } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { copyShareLink, printDocument } from "../../lib/documentActions";
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
  const toast = useToast();

  useSetDocumentCrumb(notFound ? undefined : name);

  // A party record — no lifecycle primary; the ⋯ menu carries print / export / share.
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (notFound) return [];
    return [
      { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(name) },
      { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(name) },
      {
        key: "share",
        label: t("document.share"),
        icon: "share",
        onClick: () =>
          void copyShareLink(`/purchasing/suppliers/${code}`).then((ok) =>
            toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
          ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notFound, name, code, t]);
  useSetPageActions({ menuItems: barMenu });

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
      entityType="Supplier"
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
