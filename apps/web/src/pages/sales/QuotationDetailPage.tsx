import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import {
  approveQuotation,
  convertQuotation,
  getQuotation,
  rejectQuotation,
  submitQuotation,
  type Quotation,
  type QuotationStatus,
} from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { Bdi } from "../../components/Bdi";
import { EntityLink } from "../../components/EntityLink";
import { PartyLink } from "../../components/PartyLink";
import { DocumentHeader } from "../../components/DocumentHeader";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { Disclosure } from "../../components/Disclosure";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./sales.css";

export function QuotationDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<Quotation>(
    () => getQuotation(id as string),
    [id],
    `sales:quotation:${id}`,
  );

  useSetDocumentCrumb(data?.number);

  // Optimistic state transition: flip the status instantly, reconcile with the server's quotation,
  // roll back + toast on failure.
  function act(nextStatus: QuotationStatus, request: () => Promise<Quotation>, success: string) {
    if (!data) return;
    void runOptimistic<Quotation, Quotation>({
      current: data,
      mutate,
      optimistic: (q) => ({ ...q, status: nextStatus }),
      request,
      settle: (_predicted, updated) => updated,
      toast,
      success,
    });
  }

  // Convert navigates away to the spawned order, so there's no view left to be optimistic about.
  async function onConvert(q: Quotation) {
    try {
      const res = await convertQuotation(q.id);
      navigate(`/sales/orders/${res.order_id}`);
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  if (loading) {
    return (
      <section className="sales-page">
        <ListSkeleton />
      </section>
    );
  }
  if (error || !data) {
    return (
      <section className="sales-page">
        <ErrorState message={error ?? t("common.notFound")} onRetry={reload} />
      </section>
    );
  }

  type Action = { label: string; icon?: string; onClick: () => void } | null;
  function primaryAction(): Action {
    const q = data!;
    if (q.status === "draft") return { label: t("sales.quotations.submit"), onClick: () => act("submitted", () => submitQuotation(q.id), t("sales.toast.quoteSubmitted")) };
    if (q.status === "submitted") return { label: t("sales.quotations.approve"), onClick: () => act("approved", () => approveQuotation(q.id), t("sales.toast.quoteApproved")) };
    if (q.status === "approved") return { label: t("sales.quotations.convert"), onClick: () => onConvert(q) };
    return null;
  }

  const menu: DocMenuItem[] = [
    {
      key: "duplicate",
      label: t("document.duplicate"),
      icon: "duplicate",
      onClick: () =>
        navigate("/sales/quotations/new", {
          state: {
            duplicate: {
              customer_code: data.customer_code,
              warehouse_code: data.warehouse_code,
              lines: data.lines.map((l) => ({ item_sku: l.item_sku, description: l.description, quantity: l.quantity, unit_price: l.unit_price_minor })),
            },
          },
        }),
    },
    { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(data.number) },
    { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(data.number) },
    {
      key: "share",
      label: t("document.share"),
      icon: "share",
      onClick: () => void copyShareLink(`/sales/quotations/${data.id}`).then((ok) => toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error")),
    },
  ];
  if (data.status === "submitted" || data.status === "approved") {
    menu.push({ key: "reject", label: t("sales.quotations.reject"), icon: "trash", danger: true, onClick: () => act("rejected", () => rejectQuotation(data.id, ""), t("sales.toast.quoteRejected")) });
  }

  return (
    <section className="sales-page">
      <div className="card sales-page">
        <DocumentHeader
          number={data.number}
          status={<span className={`sales-badge sales-badge--${data.status}`}>{t(`sales.quotationStatus.${data.status}`)}</span>}
          primary={primaryAction()}
          menu={menu}
          menuLabel={t("document.moreActions")}
        />
        <p className="muted docdetail__sub">
          <PartyLink type="customer" code={data.customer_code}>{data.customer_name}</PartyLink> ·{" "}
          <EntityLink type="warehouse" value={data.warehouse_code} /> · <span className="latin">{data.quote_date}</span>
        </p>

        <div className="sales-summary">
          <div className="sales-summary__item">
            <span className="sales-summary__label">{t("sales.orders.total")}</span>
            <span className="sales-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
          </div>
        </div>
      </div>

      <Disclosure summary={t("sales.detail.orderDetails")} defaultOpen>
        <div className="sales-table-wrap">
          <table className="sales-table">
            <thead>
              <tr>
                <th>{t("sales.newOrder.item")}</th>
                <th className="sales-table__num">{t("inventory.onHand.quantity")}</th>
                <th className="sales-table__num">{t("sales.newOrder.unitPrice")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l) => (
                <tr key={l.line_no}>
                  <td><EntityLink type="item" value={l.item_sku} />{l.description ? ` · ${l.description}` : ""}</td>
                  <td className="sales-table__num"><Bdi>{l.quantity}</Bdi></td>
                  <td className="sales-table__num"><Bdi>{formatMinor(l.unit_price_minor)}</Bdi></td>
                  <td className="sales-table__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>

          <dl className="sales-meta">
            <div className="sales-meta__row">
              <dt>{t("sales.quotations.approval")}</dt>
              <dd>{data.requires_approval ? t("sales.quotations.needsApproval") : t("sales.quotations.autoApprove")}</dd>
            </div>
            {data.converted_order_number && (
              <div className="sales-meta__row">
                <dt>{t("sales.quotations.convertedTo")}</dt>
                <dd className="latin"><EntityLink type="salesOrder" value={data.converted_order_number} /></dd>
              </div>
            )}
            {data.rejected_reason && (
              <div className="sales-meta__row">
                <dt>{t("sales.quotations.rejectedReason")}</dt>
                <dd>{data.rejected_reason}</dd>
              </div>
            )}
          </dl>
        </div>
      </Disclosure>
    </section>
  );
}
