import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { listCustomers, listOrders } from "../../api/sales";
import { generalLedger } from "../../api/accounting";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { formatMinor } from "../../lib/money";
import { PartyDetailView, type PartyOrderRow } from "../../components/PartyDetailView";
import { SalesNav } from "./SalesNav";
import "./sales.css";

// Accounts Receivable — the customer sub-ledger. Matches AR_ACCOUNT in erp/sales/services/orders.py.
const AR_ACCOUNT_CODE = "1100";

export function CustomerDetailPage() {
  const { t } = useTranslation();
  const { code = "" } = useParams();

  const { data: customers } = useAsync(listCustomers, [], "sales:customers");
  const { data: orders, loading, error, reload } = useAsync(() => listOrders(), [code]);
  const { data: ledger } = useAsync(
    () => generalLedger(AR_ACCOUNT_CODE, { partyType: "customer", party: code }),
    [code],
  );

  const customer = (customers ?? []).find((c) => c.code === code) ?? null;
  const mine = useMemo(
    () => (orders ?? []).filter((o) => o.customer_code === code),
    [orders, code],
  );

  const name = customer?.name ?? mine[0]?.customer_name ?? code;
  const notFound = !!customers && !!orders && !customer && mine.length === 0;
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
          void copyShareLink(`/sales/customers/${code}`).then((ok) =>
            toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
          ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notFound, name, code, t]);
  useSetPageActions({ menuItems: barMenu });

  const totalInvoiced = mine.reduce((sum, o) => sum + o.invoiced_minor, 0);
  const summary = [
    {
      label: t("sales.customer.creditLimit"),
      value: customer?.credit_limit_minor
        ? formatMinor(customer.credit_limit_minor)
        : t("sales.customer.unlimited"),
    },
    { label: t("party.ordersCount"), value: String(mine.length) },
    { label: t("party.totalInvoiced"), value: formatMinor(totalInvoiced) },
    { label: t("party.balance"), value: formatMinor(ledger?.closing_balance ?? 0) },
  ];

  const rows: PartyOrderRow[] = mine.map((o) => ({
    id: o.id,
    number: o.number,
    date: o.order_date,
    statusLabel: t(`sales.status.${o.status}`),
    total: formatMinor(o.subtotal_minor, o.currency),
    outstanding: formatMinor(o.outstanding_minor, o.currency),
    href: `/sales/orders/${o.id}`,
  }));

  return (
    <PartyDetailView
      nav={<SalesNav />}
      backHref="/sales/customers"
      backLabel={t("party.backToCustomers")}
      entityType="Customer"
      code={code}
      name={name}
      typeLabel={t("party.customer")}
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
