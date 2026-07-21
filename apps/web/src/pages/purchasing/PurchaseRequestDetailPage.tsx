import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import {
  approveRequest,
  convertRequest,
  getRequest,
  rejectRequest,
  submitRequest,
  type PRStatus,
  type PurchaseRequest,
} from "../../api/purchasing";
import { useAsync } from "../../hooks/useAsync";
import { useRecentEntity } from "../../hooks/useRecentEntity";
import { usePaletteActions, type PaletteAction } from "../../app/PaletteActionsContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../app/ToastContext";
import { useActionFeedback } from "../../app/ActionFeedbackContext";
import { showRequestReceipt, type RequestEvent } from "../../lib/feedback/purchasing";
import { runOptimistic } from "../../lib/optimistic";
import { formatMinor } from "../../lib/money";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { Bdi } from "../../components/Bdi";
import { Badge } from "../../components/Badge";
import { purchasingTone } from "../../lib/statusTone";
import { EntityLink } from "../../components/EntityLink";
import { PartyLink } from "../../components/PartyLink";
import { DocumentHeader, DocumentPrimaryButton, type DocumentPrimary } from "../../components/DocumentHeader";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { Disclosure } from "../../components/Disclosure";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { ListSkeleton } from "../../components/ListSkeleton";
import "./purchasing.css";

export function PurchaseRequestDetailPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload, mutate } = useAsync<PurchaseRequest>(
    () => getRequest(id as string),
    [id],
    `purchasing:request:${id}`,
  );
  useRecentEntity(data?.number);

  const fb = useActionFeedback();
  const location = useLocation();

  useSetDocumentCrumb(data?.number);

  const duplicate = () =>
    navigate("/purchasing/requests/new", {
      state: {
        duplicate: {
          supplier_code: data!.supplier_code,
          warehouse_code: data!.warehouse_code,
          lines: data!.lines.map((l) => ({ item_sku: l.item_sku, description: l.description, quantity: l.quantity, unit_cost: l.unit_cost_minor })),
        },
      },
    });

  // Optimistic state transition: flip the status instantly, reconcile with the server's request,
  // fire the event's rich receipt on success (roll back + error toast on failure).
  function act(nextStatus: PRStatus, request: () => Promise<PurchaseRequest>, event: RequestEvent) {
    if (!data) return;
    void runOptimistic<PurchaseRequest, PurchaseRequest>({
      current: data,
      mutate,
      optimistic: (r) => ({ ...r, status: nextStatus }),
      request,
      settle: (_predicted, updated) => updated,
      toast,
    }).then((updated) => {
      if (updated) showRequestReceipt(fb, t, updated, event, { run: runRequest, navigate, duplicate });
    });
  }

  // The receipt's recommended-next step, dispatched by current status.
  function runRequest() {
    if (!data) return;
    const r = data;
    if (r.status === "draft") act("submitted", () => submitRequest(r.id), "submitted");
    else if (r.status === "submitted") act("approved", () => approveRequest(r.id), "approved");
    else if (r.status === "approved") void onConvert(r);
  }

  // Convert navigates away to the spawned order, whose detail page fires the "converted" receipt.
  async function onConvert(r: PurchaseRequest) {
    try {
      const res = await convertRequest(r.id);
      navigate(`/purchasing/orders/${res.order_id}`, { state: { feedback: "converted" } });
    } catch (err) {
      toast.show(err instanceof Error ? err.message : String(err), "error");
    }
  }

  // A "created" receipt handed off from the new-request page fires once loaded, then clears.
  const firedIntro = useRef(false);
  useEffect(() => {
    if (firedIntro.current || !data) return;
    const intro = (location.state as { feedback?: RequestEvent } | null)?.feedback;
    if (!intro) return;
    firedIntro.current = true;
    showRequestReceipt(fb, t, data, intro, { run: runRequest, navigate, duplicate });
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
      pageActions.push({ id: "submit", label: t("purchasing.requests.submit"),
        run: () => act("submitted", () => submitRequest(data.id), "submitted") });
    }
    if (s === "submitted") {
      pageActions.push({ id: "approve", label: t("purchasing.requests.approve"),
        run: () => act("approved", () => approveRequest(data.id), "approved") });
    }
    if (s === "approved") {
      pageActions.push({ id: "convert", label: t("purchasing.requests.convert"), run: () => onConvert(data) });
    }
    // "reject" is NOT pushed here — it's already mirrored from barMenu below (useSetPageActions)
    // under the identical condition, so adding it here too would duplicate the palette row.
  }
  usePaletteActions("pr-detail", pageActions);

  // The page's ONE primary action + its ⋯ menu, published into the sticky PageHeaderBar. Memoized so
  // the published references stay stable (useSetPageActions treats them as effect deps).
  function primaryAction(): DocumentPrimary | null {
    if (!data) return null;
    const r = data;
    if (r.status === "draft") return { label: t("purchasing.requests.submit"), onClick: () => act("submitted", () => submitRequest(r.id), "submitted") };
    if (r.status === "submitted") return { label: t("purchasing.requests.approve"), onClick: () => act("approved", () => approveRequest(r.id), "approved") };
    if (r.status === "approved") return { label: t("purchasing.requests.convert"), onClick: () => onConvert(r) };
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
        onClick: () => void copyShareLink(`/purchasing/requests/${data.id}`).then((ok) => toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error")),
      },
    ];
    if (data.status === "submitted" || data.status === "approved") {
      menu.push({ key: "reject", label: t("purchasing.requests.reject"), icon: "trash", danger: true, onClick: () => act("rejected", () => rejectRequest(data.id, ""), "rejected") });
    }
    return menu;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, t]);
  useSetPageActions({ primary: barPrimary, menuItems: barMenu });

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

  return (
    <section className="pur-page">
      <div className="card pur-page">
        <DocumentHeader
          number={data.number}
          status={<Badge tone={purchasingTone(data.status)}>{t(`purchasing.requestStatus.${data.status}`)}</Badge>}
        />
        <p className="muted docdetail__sub">
          <PartyLink type="supplier" code={data.supplier_code}>{data.supplier_name}</PartyLink> ·{" "}
          <EntityLink type="warehouse" value={data.warehouse_code} /> · <span className="latin">{data.request_date}</span>
        </p>

        <div className="pur-summary">
          <div className="pur-summary__item">
            <span className="pur-summary__label">{t("sales.orders.total")}</span>
            <span className="pur-summary__value"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
          </div>
        </div>
      </div>

      <Disclosure summary={t("purchasing.detail.requestDetails")} defaultOpen>
        <div className="pur-table-wrap">
          <table className="pur-table">
            <thead>
              <tr>
                <th>{t("sales.newOrder.item")}</th>
                <th className="pur-table__num">{t("inventory.onHand.quantity")}</th>
                <th className="pur-table__num">{t("purchasing.newOrder.unitCost")}</th>
                <th className="pur-table__num">{t("sales.orders.total")}</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((l) => (
                <tr key={l.line_no}>
                  <td><EntityLink type="item" value={l.item_sku} />{l.description ? ` · ${l.description}` : ""}</td>
                  <td className="pur-table__num"><Bdi>{l.quantity}</Bdi></td>
                  <td className="pur-table__num"><Bdi>{formatMinor(l.unit_cost_minor)}</Bdi></td>
                  <td className="pur-table__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
                </tr>
              ))}
            </tbody>
          </table>

          <dl className="pur-meta">
            {(data.status === "draft" || data.status === "submitted") && (
              <div className="pur-meta__row">
                <dt>{t("purchasing.requests.approval")}</dt>
                <dd>{data.requires_approval ? t("purchasing.requests.needsApproval") : t("purchasing.requests.autoApprove")}</dd>
              </div>
            )}
            {data.converted_order_number && (
              <div className="pur-meta__row">
                <dt>{t("purchasing.requests.convertedTo")}</dt>
                <dd className="latin"><EntityLink type="purchaseOrder" value={data.converted_order_number} /></dd>
              </div>
            )}
            {data.rejected_reason && (
              <div className="pur-meta__row">
                <dt>{t("purchasing.requests.rejectedReason")}</dt>
                <dd>{data.rejected_reason}</dd>
              </div>
            )}
          </dl>
        </div>
      </Disclosure>
    </section>
  );
}
