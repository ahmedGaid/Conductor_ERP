import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router-dom";

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
import { useRecentEntity } from "../../hooks/useRecentEntity";
import { usePaletteActions, type PaletteAction } from "../../app/PaletteActionsContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { useActionFeedback } from "../../app/ActionFeedbackContext";
import { showQuotationReceipt, type QuoteEvent } from "../../lib/feedback/sales";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { Bdi } from "../../components/Bdi";
import { Badge } from "../../components/Badge";
import { salesTone } from "../../lib/statusTone";
import { EntityLink } from "../../components/EntityLink";
import { PartyLink } from "../../components/PartyLink";
import { DocumentHeader, DocumentPrimaryButton, type DocumentPrimary } from "../../components/DocumentHeader";
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
  useRecentEntity(data?.number);

  useSetDocumentCrumb(data?.number);

  const fb = useActionFeedback();
  const location = useLocation();

  const duplicate = () =>
    navigate("/sales/quotations/new", {
      state: {
        duplicate: {
          customer_code: data!.customer_code,
          warehouse_code: data!.warehouse_code,
          lines: data!.lines.map((l) => ({ item_sku: l.item_sku, description: l.description, quantity: l.quantity, unit_price: l.unit_price_minor })),
        },
      },
    });

  // Optimistic state transition: flip the status instantly, reconcile with the server's quotation,
  // fire the event's rich receipt on success (roll back + error toast on failure).
  function act(nextStatus: QuotationStatus, request: () => Promise<Quotation>, event: QuoteEvent) {
    if (!data) return;
    void runOptimistic<Quotation, Quotation>({
      current: data,
      mutate,
      optimistic: (q) => ({ ...q, status: nextStatus }),
      request,
      settle: (_predicted, updated) => updated,
      toast,
    }).then((updated) => {
      if (updated) showQuotationReceipt(fb, t, updated, event, { run: runQuote, navigate, duplicate });
    });
  }

  // The receipt's recommended-next step, dispatched by current status.
  function runQuote() {
    if (!data) return;
    const q = data;
    if (q.status === "draft") act("submitted", () => submitQuotation(q.id), "submitted");
    else if (q.status === "submitted") act("approved", () => approveQuotation(q.id), "approved");
    else if (q.status === "approved") void onConvert(q);
  }

  // Convert navigates away to the spawned order, whose detail page fires the "converted" receipt.
  async function onConvert(q: Quotation) {
    try {
      const res = await convertQuotation(q.id);
      navigate(`/sales/orders/${res.order_id}`, { state: { feedback: "converted" } });
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  // A "created" receipt handed off from the new-quotation page fires once loaded, then clears.
  const firedIntro = useRef(false);
  useEffect(() => {
    if (firedIntro.current || !data) return;
    const intro = (location.state as { feedback?: QuoteEvent } | null)?.feedback;
    if (!intro) return;
    firedIntro.current = true;
    showQuotationReceipt(fb, t, data, intro, { run: runQuote, navigate, duplicate });
    navigate(location.pathname, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // Lifecycle steps mirrored into the ⌘K "This page" group, gated by status exactly as the
  // buttons are, so the palette never offers a step that isn't the real next move. Each runs the
  // same optimistic `act`, so a palette step fires the identical rich receipt as its button.
  const pageActions: PaletteAction[] = [];
  if (data) {
    const s = data.status;
    if (s === "draft") {
      pageActions.push({ id: "submit", label: t("sales.quotations.submit"),
        run: () => act("submitted", () => submitQuotation(data.id), "submitted") });
    }
    if (s === "submitted") {
      pageActions.push({ id: "approve", label: t("sales.quotations.approve"),
        run: () => act("approved", () => approveQuotation(data.id), "approved") });
    }
    if (s === "approved") {
      pageActions.push({ id: "convert", label: t("sales.quotations.convert"), run: () => onConvert(data) });
    }
    if (s === "submitted" || s === "approved") {
      pageActions.push({ id: "reject", label: t("sales.quotations.reject"),
        run: () => act("rejected", () => rejectQuotation(data.id, ""), "rejected") });
    }
  }
  usePaletteActions("quotation-detail", pageActions);

  // The page's ONE primary action + its ⋯ menu, published into the sticky PageHeaderBar. Memoized so
  // the published references stay stable (useSetPageActions treats them as effect deps).
  function primaryAction(): DocumentPrimary | null {
    if (!data) return null;
    const q = data;
    if (q.status === "draft") return { label: t("sales.quotations.submit"), onClick: () => act("submitted", () => submitQuotation(q.id), "submitted") };
    if (q.status === "submitted") return { label: t("sales.quotations.approve"), onClick: () => act("approved", () => approveQuotation(q.id), "approved") };
    if (q.status === "approved") return { label: t("sales.quotations.convert"), onClick: () => onConvert(q) };
    return null;
  }
  const barPrimary = useMemo(() => {
    const a = primaryAction();
    return a ? <DocumentPrimaryButton action={a} /> : undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, t]);
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (!data) return [];
    const menu: DocMenuItem[] = [
      { key: "duplicate", label: t("document.duplicate"), icon: "duplicate", onClick: duplicate },
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
      menu.push({ key: "reject", label: t("sales.quotations.reject"), icon: "trash", danger: true, onClick: () => act("rejected", () => rejectQuotation(data.id, ""), "rejected") });
    }
    return menu;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, t]);
  useSetPageActions({ primary: barPrimary, menuItems: barMenu });

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

  return (
    <section className="sales-page">
      <div className="card sales-page">
        <DocumentHeader
          number={data.number}
          status={<Badge tone={salesTone(data.status)}>{t(`sales.quotationStatus.${data.status}`)}</Badge>}
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
