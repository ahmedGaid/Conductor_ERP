import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { getOrder, type SalesOrder } from "../../api/sales";
import { getOrgPreferences, type OrgPreferences } from "../../api/identity";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../app/ToastContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { ErrorState } from "../../components/ErrorState";
import { EmptyState } from "../../components/EmptyState";
import { ListSkeleton } from "../../components/ListSkeleton";
import { Bdi } from "../../components/Bdi";
import { DocumentPrimaryButton } from "../../components/DocumentHeader";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { formatMinor } from "../../lib/money";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import "./invoice.css";

// The on-brand printable invoice — the artifact the customer's customer actually sees (Identity
// System §8.1). Zero-dependency: the browser shapes Arabic (RTL) natively and "Save as PDF" in the
// print dialog produces the PDF. Monochrome throughout; the total earns its weight by a single rule
// and bold type, not colour (hierarchy by weight, never decoration).
export function InvoiceDocumentPage() {
  const { t, i18n } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, reload } = useAsync<SalesOrder>(
    () => getOrder(id as string),
    [id],
    `sales:order:${id}`,
  );
  const { data: org } = useAsync<OrgPreferences>(getOrgPreferences, [], "identity:org-preferences");
  const toast = useToast();

  useSetDocumentCrumb(data?.invoice_number);

  // The page exists to print the invoice — that is the bar's primary. Only a real, issued invoice
  // publishes actions; the not-issued designed state keeps the bar quiet.
  const hasInvoice =
    !!data &&
    (data.status === "invoiced" || data.status === "paid" || data.status === "returned") &&
    !!data.invoice_number;
  const barPrimary = useMemo(() => {
    if (!hasInvoice || !data) return undefined;
    return (
      <DocumentPrimaryButton
        action={{ label: t("document.print"), icon: "print", onClick: () => printDocument(data.invoice_number) }}
      />
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, hasInvoice, t]);
  const barMenu = useMemo<DocMenuItem[]>(() => {
    if (!hasInvoice || !data) return [];
    return [
      { key: "pdf", label: t("document.exportPdf"), icon: "download", onClick: () => printDocument(data.invoice_number) },
      {
        key: "share",
        label: t("document.share"),
        icon: "share",
        onClick: () =>
          void copyShareLink(`/sales/orders/${data.id}/invoice`).then((ok) =>
            toast.show(ok ? t("document.linkCopied") : t("document.linkCopyFailed"), ok ? "success" : "error"),
          ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, hasInvoice, t]);
  useSetPageActions({ primary: barPrimary, menuItems: barMenu });

  if (loading) {
    return (
      <section className="invoice-page">
        <ListSkeleton />
      </section>
    );
  }
  if (error || !data) {
    return (
      <section className="invoice-page">
        <ErrorState message={error ?? t("common.notFound")} onRetry={reload} />
      </section>
    );
  }

  // Only an invoiced (or later) order has a real invoice to render — anything earlier gets a designed
  // state with the one obvious way back, never a blank or a half-built document.
  const issued = data.status === "invoiced" || data.status === "paid" || data.status === "returned";
  if (!issued || !data.invoice_number) {
    return (
      <section className="invoice-page">
        <EmptyState
          title={t("sales.invoice.notIssued")}
          hint={t("sales.invoice.notIssuedHint")}
          action={{ label: t("sales.invoice.backToOrder"), to: `/sales/orders/${data.id}` }}
        />
      </section>
    );
  }

  const issueDate = new Intl.DateTimeFormat(i18n.language, { dateStyle: "long" }).format(new Date(data.order_date));
  // The invoice as issued: net + VAT, independent of any later return/payment movement on the order.
  const total = data.subtotal_minor + data.tax_minor;

  return (
    <section className="invoice-page">
      {/* The toolbar is screen-only (no-print) — it never appears on the printed/PDF artifact.
          Print/Export live in the page header bar; only the way back to the order stays here. */}
      <div className="invoice-toolbar no-print">
        <Link className="btn" to={`/sales/orders/${data.id}`}>{t("sales.invoice.backToOrder")}</Link>
      </div>

      <article className="invoice-doc card">
        <header className="invoice-doc__head">
          <div className="invoice-doc__seller">
            <h1 className="invoice-doc__org">{org?.company_name || t("sales.invoice.org")}</h1>
            <dl className="invoice-doc__id">
              {org?.vat_number && (
                <div>
                  <dt>{t("sales.invoice.taxNumber")}</dt>
                  <dd className="latin"><Bdi>{org.vat_number}</Bdi></dd>
                </div>
              )}
              {org?.country && (
                <div>
                  <dt>{t("sales.invoice.country")}</dt>
                  <dd>{org.country}</dd>
                </div>
              )}
            </dl>
          </div>
          <div className="invoice-doc__meta">
            <p className="invoice-doc__title">{t("sales.invoice.title")}</p>
            <dl className="invoice-doc__id">
              <div>
                <dt>{t("sales.detail.invoiceNo")}</dt>
                <dd className="latin"><Bdi>{data.invoice_number}</Bdi></dd>
              </div>
              <div>
                <dt>{t("sales.invoice.orderNo")}</dt>
                <dd className="latin"><Bdi>{data.number}</Bdi></dd>
              </div>
              <div>
                <dt>{t("sales.invoice.issueDate")}</dt>
                <dd>{issueDate}</dd>
              </div>
            </dl>
          </div>
        </header>

        <section className="invoice-doc__party">
          <h2 className="invoice-doc__party-label">{t("sales.invoice.billTo")}</h2>
          <p className="invoice-doc__party-name">{data.customer_name}</p>
          <p className="muted latin"><Bdi>{data.customer_code}</Bdi></p>
        </section>

        <div className="invoice-doc__lines-wrap">
          <table className="invoice-doc__lines">
          <thead>
            <tr>
              <th>{t("sales.newOrder.item")}</th>
              <th className="invoice-doc__num">{t("inventory.onHand.quantity")}</th>
              <th className="invoice-doc__num">{t("sales.newOrder.unitPrice")}</th>
              <th className="invoice-doc__num">{t("sales.newOrder.discount")}</th>
              <th className="invoice-doc__num">{t("sales.orders.total")}</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((l) => (
              <tr key={l.line_no}>
                <td>
                  <span className="latin"><Bdi>{l.item_sku}</Bdi></span>
                  {l.description ? <span className="invoice-doc__desc">{l.description}</span> : null}
                </td>
                <td className="invoice-doc__num"><Bdi>{l.quantity}</Bdi></td>
                <td className="invoice-doc__num"><Bdi>{formatMinor(l.unit_price_minor)}</Bdi></td>
                <td className="invoice-doc__num"><Bdi>{formatMinor(l.discount_minor)}</Bdi></td>
                <td className="invoice-doc__num"><Bdi>{formatMinor(l.line_total_minor)}</Bdi></td>
              </tr>
            ))}
          </tbody>
          </table>
        </div>

        <div className="invoice-doc__totals">
          <div className="invoice-doc__total-row">
            <span>{t("sales.newOrder.subtotal")}</span>
            <span className="invoice-doc__num"><Bdi>{formatMinor(data.subtotal_minor, data.currency)}</Bdi></span>
          </div>
          {data.tax_minor > 0 && (
            <div className="invoice-doc__total-row">
              <span>{t("sales.detail.vat")}{data.tax_code ? ` (${data.tax_code})` : ""}</span>
              <span className="invoice-doc__num"><Bdi>{formatMinor(data.tax_minor, data.currency)}</Bdi></span>
            </div>
          )}
          <div className="invoice-doc__total-row invoice-doc__total-row--grand">
            <span>{t("sales.orders.total")}</span>
            <span className="invoice-doc__num"><Bdi>{formatMinor(total, data.currency)}</Bdi></span>
          </div>
        </div>

        {data.notes ? <p className="invoice-doc__notes">{data.notes}</p> : null}
      </article>
    </section>
  );
}
