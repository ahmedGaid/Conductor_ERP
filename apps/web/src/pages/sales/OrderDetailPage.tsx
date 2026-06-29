import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import {
  approveOrder,
  cancelOrder,
  completeSale,
  confirmOrder,
  deliverOrder,
  getOrder,
  getOrderHistory,
  invoiceOrder,
  payOrder,
  returnOrder,
  type OrderStatus,
  type SalesOrder,
} from "../../api/sales";
import { useAsync } from "../../hooks/useAsync";
import { usePreferences } from "../../preferences/PreferencesContext";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { Bdi } from "../../components/Bdi";
import { PartyLink } from "../../components/PartyLink";
import { EntityLink } from "../../components/EntityLink";
import { DocumentHeader } from "../../components/DocumentHeader";
import { DocumentStatusNote, type StatusTone } from "../../components/DocumentStatusNote";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { WorkflowTracker } from "../../components/WorkflowTracker";
import { workflowFor } from "../../lib/workflow";
import { Disclosure } from "../../components/Disclosure";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./sales.css";

// Plain-language explanation of the current state and the next step (human language over the bare
// status word). The draft+approval case gets its own "waiting for approval" message.
function statusExplainKey(o: SalesOrder): string {
  if (o.status === "draft" && o.requires_approval && !o.approved) return "awaitingApproval";
  return o.status;
}

// Lifecycle states still open to cancellation under the org policy (the service enforces the same).
function isCancellable(status: OrderStatus, until: string | undefined): boolean {
  if (until === "draft") return status === "draft";
  if (until === "confirmed") return status === "draft" || status === "confirmed";
  return false; // "disabled" or unknown
}

export function OrderDetailPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { prefs } = usePreferences();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<SalesOrder>(
    () => getOrder(id as string),
    [id],
    `sales:order:${id}`,
  );
  // The lifecycle trail behind each tracker stage. Loads with the page; the snapshot is historical,
  // so it doesn't need to follow in-page optimistic flips (it refreshes on the next visit/reload).
  const { data: history } = useAsync(() => getOrderHistory(id as string), [id], `sales:order:${id}:history`);
  const [confirmCancel, setConfirmCancel] = useState(false);

  useSetDocumentCrumb(data?.number);

  // Optimistic: apply the predicted change (status flip, approval flag) so the badge, explainer
  // and action set update instantly, then let the server's returned order reconcile the derived
  // amounts (invoiced/outstanding/…). A failure rolls the whole order back and shows an error toast.
  function act(
    apply: (order: SalesOrder) => SalesOrder,
    request: () => Promise<SalesOrder>,
    success: string,
    successFrom?: (updated: SalesOrder) => string,
  ) {
    if (!data) return;
    void runOptimistic<SalesOrder, SalesOrder>({
      current: data,
      mutate,
      optimistic: apply,
      request,
      settle: (_predicted, updated) => updated,
      toast,
      success,
      successFrom,
    });
  }

  const setStatus = (status: OrderStatus) => (order: SalesOrder): SalesOrder => ({ ...order, status });

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

  // --- Primary lifecycle action (the one most-likely next step). ---
  type Action = { label: string; icon?: string; onClick: () => void } | null;
  function primaryAction(): Action {
    const o = data!;
    if (o.status === "draft" && o.requires_approval && !o.approved) {
      return { label: t("sales.detail.approve"), onClick: () => act((x) => ({ ...x, approved: true }), () => approveOrder(o.id), t("sales.toast.approved")) };
    }
    if (o.status === "draft") {
      return { label: t("sales.detail.confirm"), onClick: () => act(setStatus("confirmed"), () => confirmOrder(o.id), t("sales.toast.confirmed")) };
    }
    if (o.status === "confirmed" || o.status === "partially_delivered") {
      return {
        label: o.status === "partially_delivered" ? t("sales.detail.deliverRemaining") : t("sales.detail.deliver"),
        onClick: () => act(setStatus("delivered"), () => deliverOrder(o.id), t("sales.toast.delivered")),
      };
    }
    if (o.status === "delivered") {
      return { label: t("sales.detail.invoice"), onClick: () => act(setStatus("invoiced"), () => invoiceOrder(o.id), t("sales.toast.invoiced"), (u) => t("sales.toast.invoicedDone", { no: u.invoice_number })) };
    }
    if (o.status === "invoiced") {
      return { label: t("sales.detail.recordPayment"), onClick: () => act(setStatus("paid"), () => payOrder(o.id, o.outstanding_minor), t("sales.toast.paid")) };
    }
    if (o.status === "paid") {
      return { label: t("sales.detail.return"), icon: "rotate", onClick: () => act(setStatus("returned"), () => returnOrder(o.id), t("sales.toast.returned"), (u) => t("sales.toast.returnedDone", { no: u.credit_note_number })) };
    }
    return null;
  }

  // --- ⋯ overflow menu. ---
  const cancellable = isCancellable(data.status, prefs?.order_cancel_until);
  const menu: DocMenuItem[] = [
    {
      key: "duplicate",
      label: t("document.duplicate"),
      icon: "duplicate",
      onClick: () =>
        navigate("/sales/orders/new", {
          state: {
            duplicate: {
              customer_code: data.customer_code,
              warehouse_code: data.warehouse_code,
              tax_code: data.tax_code,
              lines: data.lines.map((l) => ({
                item_sku: l.item_sku,
                description: l.description,
                quantity: l.quantity,
                unit_price: l.unit_price_minor,
                discount: l.discount_minor,
              })),
            },
          },
        }),
    },
    { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(data.number) },
    {
      key: "pdf",
      label: t("document.exportPdf"),
      icon: "download",
      // Once invoiced, "Export PDF" opens the on-brand invoice document (the artifact the customer's
      // customer sees); before that it just prints the order copy.
      onClick: () =>
        data.invoice_number ? navigate(`/sales/orders/${data.id}/invoice`) : printDocument(data.number),
    },
    {
      key: "share",
      label: t("document.share"),
      icon: "share",
      onClick: () =>
        void copyShareLink(`/go/sales_order/${data.number}`).then((ok) =>
          toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
        ),
    },
  ];
  // Fast-path the same-day counter sale: drive draft→confirmed→delivered→invoiced in one move.
  // Additive shortcut to the granular primary action; hidden once nothing remains to fast-path or
  // when an above-threshold order still needs its approval (the server would refuse the confirm step).
  const canFastPath =
    (data.status === "draft" || data.status === "confirmed" || data.status === "partially_delivered") &&
    !(data.requires_approval && !data.approved);
  if (canFastPath) {
    menu.unshift({
      key: "complete",
      label: t("sales.detail.completeSale"),
      icon: "checkCircle",
      onClick: () =>
        act(
          setStatus("invoiced"),
          () => completeSale(data.id),
          t("sales.toast.completed"),
          (u) => t("sales.toast.invoicedDone", { no: u.invoice_number }),
        ),
    });
  }
  // Once invoiced, the e-invoice submit is reachable straight from the order (no context switch to
  // the E-invoicing list) — deep-links to that invoice, focused and ready to submit.
  if ((data.status === "invoiced" || data.status === "paid") && data.invoice_number) {
    menu.push({
      key: "einvoice",
      label: t("sales.detail.sendEinvoice"),
      icon: "einvoice",
      onClick: () => navigate(`/einvoice?focus=${encodeURIComponent(data.invoice_number)}`),
    });
  }
  // Return is reachable from the menu while it isn't the primary action (i.e. on an invoiced order).
  if (data.status === "invoiced") {
    menu.push({
      key: "return",
      label: t("sales.detail.return"),
      icon: "rotate",
      onClick: () => act(setStatus("returned"), () => returnOrder(data.id), t("sales.toast.returned"), (u) => t("sales.toast.returnedDone", { no: u.credit_note_number })),
    });
  }
  if (cancellable) {
    menu.push({ key: "cancel", label: t("document.cancelOrder"), icon: "trash", danger: true, onClick: () => setConfirmCancel(true) });
  }

  // --- State note (icon + plain language). ---
  const terminal = data.status === "paid" || data.status === "returned" || data.status === "cancelled";
  const tone: StatusTone = data.status === "paid" ? "done" : data.status === "returned" || data.status === "cancelled" ? "exception" : "active";
  const completedAt = history && history.length > 0 ? history[history.length - 1].at : null;
  const completedOn = completedAt ? new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium" }).format(new Date(completedAt)) : null;

  return (
    <section className="sales-page">
      <div className="card sales-page">
        <DocumentHeader
          number={data.number}
          status={<span className={`sales-badge sales-badge--${data.status}`}>{t(`sales.status.${data.status}`)}</span>}
          primary={primaryAction()}
          menu={menu}
          menuLabel={t("document.moreActions")}
        />
        <p className="muted docdetail__sub">
          <PartyLink type="customer" code={data.customer_code}>{data.customer_name}</PartyLink> ·{" "}
          <EntityLink type="warehouse" value={data.warehouse_code} /> · <span className="latin">{data.order_date}</span>
        </p>

        <DocumentStatusNote
          tone={tone}
          title={t(`sales.statusExplain.${statusExplainKey(data)}`, { amount: formatMinor(data.outstanding_minor, data.currency) })}
          detail={terminal && completedOn ? t("document.completedOn", { date: completedOn }) : undefined}
        />

        <hr className="docdetail__rule" />

        <WorkflowTracker
          kind="sales"
          steps={workflowFor("sales", data.status)}
          history={history ?? undefined}
          docs={{ orderNumber: data.number, invoiceNumber: data.invoice_number, creditNoteNumber: data.credit_note_number }}
        />

        <hr className="docdetail__rule" />

        <div className="sales-summary">
          <div className="sales-summary__item">
            <span className="sales-summary__label">{t("sales.orders.total")}</span>
            <span className="sales-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
          </div>
          {data.tax_minor > 0 && (
            <div className="sales-summary__item">
              <span className="sales-summary__label">{t("sales.detail.vat")}{data.tax_code ? ` (${data.tax_code})` : ""}</span>
              <span className="sales-summary__value"><Bdi>{formatMinor(data.tax_minor, data.currency)}</Bdi></span>
            </div>
          )}
          <div className="sales-summary__item">
            <span className="sales-summary__label">{t("sales.detail.invoiced")}</span>
            <span className="sales-summary__value"><Bdi>{formatMinor(data.invoiced_minor, data.currency)}</Bdi></span>
          </div>
          <div className="sales-summary__item">
            <span className="sales-summary__label">{t("sales.detail.outstanding")}</span>
            <span className="sales-summary__value"><Bdi>{formatMinor(data.outstanding_minor, data.currency)}</Bdi></span>
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
                <th className="sales-table__num">{t("sales.detail.delivered")}</th>
                <th className="sales-table__num">{t("sales.detail.returnedQty")}</th>
                <th className="sales-table__num">{t("sales.newOrder.unitPrice")}</th>
                <th className="sales-table__num">{t("sales.newOrder.discount")}</th>
                <th className="sales-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l) => (
                <tr key={l.line_no}>
                  <td><EntityLink type="item" value={l.item_sku} />{l.description ? ` · ${l.description}` : ""}</td>
                  <td className="sales-table__num"><Bdi>{l.quantity}</Bdi></td>
                  <td className="sales-table__num"><Bdi>{l.delivered_qty}</Bdi></td>
                  <td className="sales-table__num"><Bdi>{l.returned_qty}</Bdi></td>
                  <td className="sales-table__num"><Bdi>{formatMinor(l.unit_price_minor)}</Bdi></td>
                  <td className="sales-table__num"><Bdi>{formatMinor(l.discount_minor)}</Bdi></td>
                  <td className="sales-table__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>

          {(data.invoice_number || data.credit_note_number || data.returned_minor > 0 || data.requires_approval) && (
            <dl className="sales-meta">
              {data.invoice_number && (
                <div className="sales-meta__row">
                  <dt>{t("sales.detail.invoiceNo")}</dt>
                  <dd className="latin"><EntityLink type="journal" value={data.invoice_number} /></dd>
                </div>
              )}
              {data.credit_note_number && (
                <div className="sales-meta__row">
                  <dt>{t("sales.detail.creditNoteNo")}</dt>
                  <dd className="latin"><EntityLink type="journal" value={data.credit_note_number} /></dd>
                </div>
              )}
              {data.returned_minor > 0 && (
                <div className="sales-meta__row">
                  <dt>{t("sales.detail.returned")}</dt>
                  <dd><Bdi>{formatMinor(data.returned_minor, data.currency)}</Bdi></dd>
                </div>
              )}
              {data.requires_approval && (
                <div className="sales-meta__row">
                  <dt>{t("sales.detail.approval")}</dt>
                  <dd>{data.approved ? t("sales.detail.approved") : t("sales.detail.pendingApproval")}</dd>
                </div>
              )}
            </dl>
          )}
        </div>
      </Disclosure>

      <ConfirmDialog
        open={confirmCancel}
        title={t("document.cancelConfirmTitle", { number: data.number })}
        body={t("document.cancelConfirmBody")}
        confirmLabel={t("document.cancelOrder")}
        danger
        onConfirm={() => act(setStatus("cancelled"), () => cancelOrder(data.id), t("sales.toast.cancelled"))}
        onClose={() => setConfirmCancel(false)}
      />
    </section>
  );
}
