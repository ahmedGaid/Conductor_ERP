import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import {
  approvePO,
  billPO,
  cancelPO,
  confirmPO,
  getPurchaseOrder,
  getPurchaseOrderHistory,
  payPO,
  receivePO,
  returnPO,
  type POStatus,
  type PurchaseOrder,
} from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { usePreferences } from "../../preferences/PreferencesContext";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { useActionFeedback } from "../../app/ActionFeedbackContext";
import { showPurchaseOrderReceipt, showPurchaseOrderError, type POActionKey, type POEvent } from "../../lib/feedback/purchasing";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { Bdi } from "../../components/Bdi";
import { Badge } from "../../components/Badge";
import { purchasingTone } from "../../lib/statusTone";
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
import "./purchasing.css";

function statusExplainKey(o: PurchaseOrder): string {
  if (o.status === "draft" && o.requires_approval && !o.approved) return "awaitingApproval";
  return o.status;
}

function isCancellable(status: POStatus, until: string | undefined): boolean {
  if (until === "draft") return status === "draft";
  if (until === "confirmed") return status === "draft" || status === "confirmed";
  return false;
}

export function PurchaseOrderDetailPage() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { prefs } = usePreferences();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<PurchaseOrder>(
    () => getPurchaseOrder(id as string),
    [id],
    `purchasing:order:${id}`,
  );
  const { data: history } = useAsync(
    () => getPurchaseOrderHistory(id as string),
    [id],
    `purchasing:order:${id}:history`,
  );
  const [confirmCancel, setConfirmCancel] = useState(false);
  const fb = useActionFeedback();
  const location = useLocation();

  useSetDocumentCrumb(data?.number);

  // Duplicate / print — shared by the ⋯ menu and the receipt's quick actions.
  const duplicate = () =>
    navigate("/purchasing/orders/new", {
      state: {
        duplicate: {
          supplier_code: data!.supplier_code,
          warehouse_code: data!.warehouse_code,
          tax_code: data!.tax_code,
          lines: data!.lines.map((l) => ({
            item_sku: l.item_sku,
            description: l.description,
            quantity: l.quantity,
            unit_cost: l.unit_cost_minor,
          })),
        },
      },
    });
  const print = () => printDocument(data!.number);

  // Optimistic: apply the predicted change (status flip, approval flag) so the badge, explainer and
  // action set update instantly, then let the server's returned order reconcile the derived amounts
  // (billed/outstanding/…). On success the event's rich receipt fires; a failure rolls the whole
  // order back and shows a rich error receipt (both handled via runOptimistic).
  function act(apply: (order: PurchaseOrder) => PurchaseOrder, request: () => Promise<PurchaseOrder>, event: POEvent) {
    if (!data) return;
    const snapshot = data;
    void runOptimistic<PurchaseOrder, PurchaseOrder>({
      current: data,
      mutate,
      optimistic: apply,
      request,
      settle: (_predicted, updated) => updated,
      toast,
      onError: (error) => showPurchaseOrderError(fb, t, snapshot, event, error, { run: runAction }),
    }).then((updated) => {
      if (updated) showPurchaseOrderReceipt(fb, t, updated, event, { run: runAction, navigate, duplicate, print });
    });
  }

  const setStatus = (status: POStatus) => (order: PurchaseOrder): PurchaseOrder => ({ ...order, status });

  // Map a receipt's recommended-next key back to the matching optimistic action.
  function runAction(key: POActionKey) {
    if (!data) return;
    const o = data;
    switch (key) {
      case "approve": act((x) => ({ ...x, approved: true }), () => approvePO(o.id), "approved"); break;
      case "confirm": act(setStatus("confirmed"), () => confirmPO(o.id), "confirmed"); break;
      case "receive": act(setStatus("received"), () => receivePO(o.id), "received"); break;
      case "bill": act(setStatus("billed"), () => billPO(o.id), "billed"); break;
      case "pay": act(setStatus("paid"), () => payPO(o.id, o.outstanding_minor), "paid"); break;
      case "return": act(setStatus("returned"), () => returnPO(o.id), "returned"); break;
    }
  }

  // A rich receipt handed off from creation / conversion fires once the order has loaded, then the
  // marker is cleared from history state so it never re-fires on back/refresh.
  const firedIntro = useRef(false);
  useEffect(() => {
    if (firedIntro.current || !data) return;
    const intro = (location.state as { feedback?: POEvent } | null)?.feedback;
    if (!intro) return;
    firedIntro.current = true;
    showPurchaseOrderReceipt(fb, t, data, intro, { run: runAction, navigate, duplicate, print });
    navigate(location.pathname, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  if (loading) {
    return (
      <section className="pur-page">
        <ListSkeleton />
      </section>
    );
  }
  if (error || !data) {
    return (
      <section className="pur-page">
        <ErrorState message={error ?? t("common.notFound")} onRetry={reload} />
      </section>
    );
  }

  type Action = { label: string; icon?: string; onClick: () => void } | null;
  function primaryAction(): Action {
    const o = data!;
    if (o.status === "draft" && o.requires_approval && !o.approved) {
      return { label: t("purchasing.detail.approve"), onClick: () => act((x) => ({ ...x, approved: true }), () => approvePO(o.id), "approved") };
    }
    if (o.status === "draft") {
      return { label: t("purchasing.detail.confirm"), onClick: () => act(setStatus("confirmed"), () => confirmPO(o.id), "confirmed") };
    }
    if (o.status === "confirmed" || o.status === "partially_received") {
      return {
        label: o.status === "partially_received" ? t("purchasing.detail.receiveRemaining") : t("purchasing.detail.receive"),
        onClick: () => act(setStatus("received"), () => receivePO(o.id), "received"),
      };
    }
    if (o.status === "received") {
      return { label: t("purchasing.detail.bill"), onClick: () => act(setStatus("billed"), () => billPO(o.id), "billed") };
    }
    if (o.status === "billed") {
      return { label: t("purchasing.detail.recordPayment"), onClick: () => act(setStatus("paid"), () => payPO(o.id, o.outstanding_minor), "paid") };
    }
    if (o.status === "paid") {
      return { label: t("purchasing.detail.return"), icon: "rotate", onClick: () => act(setStatus("returned"), () => returnPO(o.id), "returned") };
    }
    return null;
  }

  const cancellable = isCancellable(data.status, prefs?.order_cancel_until);
  const menu: DocMenuItem[] = [
    { key: "duplicate", label: t("document.duplicate"), icon: "duplicate", onClick: duplicate },
    { key: "print", label: t("document.print"), icon: "print", onClick: () => printDocument(data.number) },
    { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(data.number) },
    {
      key: "share",
      label: t("document.share"),
      icon: "share",
      onClick: () =>
        void copyShareLink(`/go/purchase_order/${data.number}`).then((ok) =>
          toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
        ),
    },
  ];
  if (data.status === "billed") {
    menu.push({
      key: "return",
      label: t("purchasing.detail.return"),
      icon: "rotate",
      onClick: () => act(setStatus("returned"), () => returnPO(data.id), "returned"),
    });
  }
  if (cancellable) {
    menu.push({ key: "cancel", label: t("document.cancelOrder"), icon: "trash", danger: true, onClick: () => setConfirmCancel(true) });
  }

  const terminal = data.status === "paid" || data.status === "returned" || data.status === "cancelled";
  const tone: StatusTone = data.status === "paid" ? "done" : data.status === "returned" || data.status === "cancelled" ? "exception" : "active";
  const completedAt = history && history.length > 0 ? history[history.length - 1].at : null;
  const completedOn = completedAt ? new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium" }).format(new Date(completedAt)) : null;

  return (
    <section className="pur-page">
      <div className="card pur-page">
        <DocumentHeader
          number={data.number}
          status={<Badge tone={purchasingTone(data.status)}>{t(`purchasing.status.${data.status}`)}</Badge>}
          primary={primaryAction()}
          menu={menu}
          menuLabel={t("document.moreActions")}
        />
        <p className="muted docdetail__sub">
          <PartyLink type="supplier" code={data.supplier_code}>{data.supplier_name}</PartyLink> ·{" "}
          <EntityLink type="warehouse" value={data.warehouse_code} /> · <span className="latin">{data.order_date}</span>
        </p>

        <DocumentStatusNote
          tone={tone}
          title={t(`purchasing.statusExplain.${statusExplainKey(data)}`, { amount: formatMinor(data.outstanding_minor, data.currency) })}
          detail={terminal && completedOn ? t("document.completedOn", { date: completedOn }) : undefined}
        />

        <hr className="docdetail__rule" />

        <WorkflowTracker
          kind="purchasing"
          steps={workflowFor("purchasing", data.status)}
          history={history ?? undefined}
          docs={{ orderNumber: data.number, invoiceNumber: data.bill_number, creditNoteNumber: data.debit_note_number }}
        />

        <hr className="docdetail__rule" />

        <div className="pur-summary">
          <div className="pur-summary__item">
            <span className="pur-summary__label">{t("sales.orders.total")}</span>
            <span className="pur-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
          </div>
          {data.tax_minor > 0 && (
            <div className="pur-summary__item">
              <span className="pur-summary__label">{t("purchasing.detail.vat")}</span>
              <span className="pur-summary__value"><Bdi>{formatMinor(data.tax_minor, data.currency)}</Bdi></span>
            </div>
          )}
          <div className="pur-summary__item">
            <span className="pur-summary__label">{t("purchasing.detail.billed")}</span>
            <span className="pur-summary__value"><Bdi>{formatMinor(data.billed_minor, data.currency)}</Bdi></span>
          </div>
          <div className="pur-summary__item">
            <span className="pur-summary__label">{t("purchasing.detail.outstanding")}</span>
            <span className="pur-summary__value"><Bdi>{formatMinor(data.outstanding_minor, data.currency)}</Bdi></span>
          </div>
        </div>
      </div>

      <Disclosure summary={t("purchasing.detail.orderDetails")} defaultOpen>
        <div className="pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <th>{t("sales.newOrder.item")}</th>
                <th className="pur-table__num">{t("inventory.onHand.quantity")}</th>
                <th className="pur-table__num">{t("purchasing.detail.received")}</th>
                <th className="pur-table__num">{t("purchasing.detail.returnedQty")}</th>
                <th className="pur-table__num">{t("purchasing.newOrder.unitCost")}</th>
                <th className="pur-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l) => (
                <tr key={l.line_no}>
                  <td><EntityLink type="item" value={l.item_sku} />{l.description ? ` · ${l.description}` : ""}</td>
                  <td className="pur-table__num"><Bdi>{l.quantity}</Bdi></td>
                  <td className="pur-table__num"><Bdi>{l.received_qty}</Bdi></td>
                  <td className="pur-table__num"><Bdi>{l.returned_qty}</Bdi></td>
                  <td className="pur-table__num"><Bdi>{formatMinor(l.unit_cost_minor)}</Bdi></td>
                  <td className="pur-table__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>

          {(data.bill_number || data.debit_note_number || data.returned_minor > 0 || data.requires_approval) && (
            <dl className="pur-meta">
              {data.bill_number && (
                <div className="pur-meta__row">
                  <dt>{t("purchasing.detail.billNo")}</dt>
                  <dd className="latin"><EntityLink type="journal" value={data.bill_number} /></dd>
                </div>
              )}
              {data.debit_note_number && (
                <div className="pur-meta__row">
                  <dt>{t("purchasing.detail.debitNoteNo")}</dt>
                  <dd className="latin"><EntityLink type="journal" value={data.debit_note_number} /></dd>
                </div>
              )}
              {data.returned_minor > 0 && (
                <div className="pur-meta__row">
                  <dt>{t("purchasing.detail.returned")}</dt>
                  <dd><Bdi>{formatMinor(data.returned_minor, data.currency)}</Bdi></dd>
                </div>
              )}
              {data.requires_approval && (
                <div className="pur-meta__row">
                  <dt>{t("purchasing.detail.approval")}</dt>
                  <dd>{data.approved ? t("purchasing.detail.approved") : t("purchasing.detail.pendingApproval")}</dd>
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
        onConfirm={() => act(setStatus("cancelled"), () => cancelPO(data.id), "cancelled")}
        onClose={() => setConfirmCancel(false)}
      />
    </section>
  );
}
