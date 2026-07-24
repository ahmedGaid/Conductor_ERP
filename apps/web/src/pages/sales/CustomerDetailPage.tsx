import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { listCustomers, listOrders, updateCustomer, type Customer } from "../../api/sales";
import { generalLedger } from "../../api/accounting";
import { listCustomFieldDefs } from "../../api/customFields";
import { buildCustomData, validateCustomFieldValues, formatCustomFieldValue, type CustomFieldValues } from "../../lib/customFields";
import { CustomFieldsForm } from "../../components/CustomFieldsForm";
import { useAsync } from "../../hooks/useAsync";
import { useDraftRecovery } from "../../hooks/useDraftRecovery";
import { useToast } from "../../app/ToastContext";
import { useSetPageActions } from "../../app/PageActionsContext";
import { useSetDocumentCrumb } from "../../app/DocumentCrumb";
import { type DocMenuItem } from "../../components/DocumentMenu";
import { copyShareLink, printDocument } from "../../lib/documentActions";
import { formatMinor, minorToAmount, parseToMinor } from "../../lib/money";
import { Disclosure } from "../../components/Disclosure";
import { DraftRecoveryBanner } from "../../components/DraftRecoveryBanner";
import { DraftStatusIndicator } from "../../components/DraftStatusIndicator";
import { PartyDetailView, type PartyOrderRow } from "../../components/PartyDetailView";
import { SalesNav } from "./SalesNav";
import "./sales.css";

interface CustomerEditDraft {
  name: string;
  limit: string;
  taxReg: string;
  nationalId: string;
  custom: CustomFieldValues;
}

function draftFrom(c: Customer | null): CustomerEditDraft {
  return {
    name: c?.name ?? "", limit: c?.credit_limit_minor ? minorToAmount(c.credit_limit_minor) : "",
    taxReg: c?.tax_registration_number ?? "", nationalId: c?.national_id ?? "",
    custom: (c?.custom_data as CustomFieldValues | undefined) ?? {},
  };
}

// Accounts Receivable — the customer sub-ledger. Matches AR_ACCOUNT in erp/sales/services/orders.py.
const AR_ACCOUNT_CODE = "1100";

export function CustomerDetailPage() {
  const { t, i18n } = useTranslation();
  const isArabic = i18n.resolvedLanguage?.startsWith("ar") ?? true;
  const { code = "" } = useParams();

  const { data: customers, reload: reloadCustomers } = useAsync(listCustomers, [], "sales:customers");
  const { data: customFieldDefs } = useAsync(
    () => listCustomFieldDefs("sales.customer"),
    [],
    "settings:customFields:sales.customer",
  );
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

  // Edit form — local state synced once from the loaded record, then edited freely (a background
  // refresh from our own save must not clobber mid-typing state, hence the once-per-record sync).
  const [editName, setEditName] = useState("");
  const [editLimit, setEditLimit] = useState("");
  const [editTaxReg, setEditTaxReg] = useState("");
  const [editNationalId, setEditNationalId] = useState("");
  const [editCustom, setEditCustom] = useState<CustomFieldValues>({});
  const [editIdentityError, setEditIdentityError] = useState("");
  const [editCustomErrors, setEditCustomErrors] = useState<Record<string, string>>({});
  const [editBusy, setEditBusy] = useState(false);
  const toastEdit = useToast();
  useEffect(() => {
    if (!customer) return;
    setEditName(customer.name);
    setEditLimit(customer.credit_limit_minor ? minorToAmount(customer.credit_limit_minor) : "");
    setEditTaxReg(customer.tax_registration_number);
    setEditNationalId(customer.national_id);
    setEditCustom((customer.custom_data as CustomFieldValues | undefined) ?? {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customer?.code]);

  const editBaseline = useMemo(() => draftFrom(customer), [customer]);
  const editDraft = useMemo<CustomerEditDraft>(
    () => ({ name: editName, limit: editLimit, taxReg: editTaxReg, nationalId: editNationalId, custom: editCustom }),
    [editName, editLimit, editTaxReg, editNationalId, editCustom],
  );
  const editRecovery = useDraftRecovery<CustomerEditDraft>({
    workflowKey: "sales.customer.edit",
    entityType: "customer",
    relatedEntityId: code,
    value: editDraft,
    baseline: editBaseline,
    schemaVersion: 1,
    enabled: !!customer,
  });

  function applyEditDraft(d: CustomerEditDraft) {
    setEditName(d.name ?? "");
    setEditLimit(d.limit ?? "");
    setEditTaxReg(d.taxReg ?? "");
    setEditNationalId(d.nationalId ?? "");
    setEditCustom(d.custom ?? {});
  }

  async function onSaveEdit() {
    const national = editNationalId.trim();
    const taxRegistration = editTaxReg.trim();
    if (national && !/^\d{14}$/.test(national)) {
      setEditIdentityError(t("sales.customer.nationalIdInvalid"));
      return;
    }
    if (taxRegistration && !/^\d+$/.test(taxRegistration)) {
      setEditIdentityError(t("sales.customer.taxRegInvalid"));
      return;
    }
    setEditIdentityError("");
    const defs = customFieldDefs ?? [];
    const errors = validateCustomFieldValues(defs, editCustom);
    if (Object.keys(errors).length > 0) {
      setEditCustomErrors(errors);
      return;
    }
    setEditCustomErrors({});
    setEditBusy(true);
    try {
      await updateCustomer(code, {
        name: editName.trim(),
        credit_limit_minor: parseToMinor(editLimit) ?? 0,
        tax_registration_number: taxRegistration,
        national_id: national,
        custom_data: buildCustomData(defs, editCustom),
      });
      void editRecovery.complete(code);
      reloadCustomers();
      toastEdit.show(t("common.saved"), "success");
    } catch (err) {
      toastEdit.show(err instanceof Error ? err.message : String(err), "error");
    } finally {
      setEditBusy(false);
    }
  }

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
    ...(customFieldDefs ?? [])
      .map((def) => ({
        label: isArabic ? def.label_ar : def.label_en,
        value: formatCustomFieldValue(def, customer?.custom_data?.[def.key]),
      }))
      .filter((row) => row.value !== ""),
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
      extra={
        !notFound && customer ? (
          <>
            {editRecovery.recoverable && (
              <DraftRecoveryBanner
                entityLabel={t("drafts.workflow.sales.customer.edit")}
                lastActiveAt={editRecovery.recoverable.lastActiveAt}
                onContinue={() => {
                  const payload = editRecovery.recover();
                  if (payload) applyEditDraft(payload);
                }}
                onDiscard={() => void editRecovery.discard()}
              />
            )}
            <Disclosure summary={t("party.editCustomer")}>
              <div className="card sales-toolbar">
                <label className="sales-field">
                  <span>{t("sales.customer.name")}</span>
                  <input value={editName} onChange={(e) => setEditName(e.target.value)} required />
                </label>
                <label className="sales-field">
                  <span>{t("sales.customer.creditLimit")}</span>
                  <input className="latin" inputMode="decimal" value={editLimit} onChange={(e) => setEditLimit(e.target.value)} placeholder="0.00" />
                </label>
                <label className="sales-field">
                  <span>{t("sales.customer.taxRegistrationNumber")}</span>
                  <input className="latin" inputMode="numeric" value={editTaxReg} onChange={(e) => setEditTaxReg(e.target.value)} placeholder={t("sales.customer.optional")} />
                </label>
                <label className="sales-field">
                  <span>{t("sales.customer.nationalId")}</span>
                  <input className="latin" inputMode="numeric" value={editNationalId} onChange={(e) => setEditNationalId(e.target.value)} placeholder={t("sales.customer.nationalIdHint")} />
                </label>
                {editIdentityError && <p className="custom-field-error" role="alert">{editIdentityError}</p>}
                <CustomFieldsForm
                  defs={customFieldDefs ?? []}
                  values={editCustom}
                  onChange={(k, v) => setEditCustom((prev) => ({ ...prev, [k]: v }))}
                  errors={editCustomErrors}
                  fieldClassName="sales-field"
                />
                {editRecovery.conflict && <p className="muted" role="status">{t("drafts.conflict")}</p>}
                <DraftStatusIndicator status={editRecovery.status} savedAt={editRecovery.savedAt} />
                <button type="button" className="btn btn--primary" onClick={() => void onSaveEdit()} disabled={editBusy}>
                  {t("common.save")}
                </button>
              </div>
            </Disclosure>
          </>
        ) : undefined
      }
    />
  );
}
