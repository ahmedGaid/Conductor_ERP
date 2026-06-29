import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";

import { NavIcon } from "./icons";
import { useDocumentCrumb } from "./DocumentCrumb";
import "./RouteBreadcrumb.css";

function Chevron() {
  return (
    <svg className="crumb__chev" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="m9 6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * Route-driven breadcrumb shown above every module work page (Sales, Purchasing,
 * Inventory, Accounting, CRM — not settings/admin/dashboard). Identity is icon +
 * place: [module glyph] Module › Section. Monochrome; the module's colour reaches
 * it only through the inherited --color-accent on hover. The section label reuses
 * the module's existing tab labels, so it always matches the nav.
 */

const MODULE_SET = new Set(["sales", "purchasing", "inventory", "accounting", "crm"]);

// Landing section for each module's bare "/module" route.
const DEFAULT_SECTION: Record<string, string> = {
  sales: "sales.tabs.orders",
  purchasing: "purchasing.tabs.orders",
  inventory: "inventory.tabs.stockOnHand",
  accounting: "accounting.tabs.chart",
  crm: "crm.tabs.pipeline",
};

// seg2 (or "seg2/seg3" for create forms) → tab-label key. Detail pages (.../:id)
// fall through to the seg2 entry, so an order detail still reads "Orders".
const SECTIONS: Record<string, Record<string, string>> = {
  sales: {
    orders: "sales.tabs.orders",
    "orders/new": "sales.tabs.newOrder",
    quotations: "sales.tabs.quotations",
    customers: "sales.tabs.customers",
  },
  purchasing: {
    orders: "purchasing.tabs.orders",
    "orders/new": "purchasing.tabs.newOrder",
    requests: "purchasing.tabs.requests",
    "requests/new": "purchasing.tabs.newRequest",
    suppliers: "purchasing.tabs.suppliers",
  },
  inventory: {
    items: "inventory.tabs.items",
    warehouses: "inventory.tabs.warehouses",
    movements: "inventory.tabs.movements",
    counts: "inventory.tabs.counts",
    batches: "inventory.tabs.batches",
  },
  accounting: {
    journals: "accounting.tabs.journals",
    "journals/new": "accounting.tabs.newEntry",
    chart: "accounting.tabs.chart",
    "trial-balance": "accounting.tabs.trialBalance",
    "general-ledger": "accounting.tabs.generalLedger",
    "income-statement": "accounting.tabs.incomeStatement",
    "balance-sheet": "accounting.tabs.balanceSheet",
    "cash-flow": "accounting.tabs.cashFlow",
    "vat-return": "accounting.tabs.vatReturn",
    "fixed-assets": "accounting.tabs.fixedAssets",
    "cost-centers": "accounting.tabs.costCenters",
    budgets: "accounting.tabs.budgets",
  },
  crm: {
    pipeline: "crm.tabs.pipeline",
    leads: "crm.tabs.leads",
    tickets: "crm.tabs.tickets",
    campaigns: "crm.tabs.campaigns",
  },
};

function sectionKey(module: string, seg2: string, seg3: string): string | null {
  if (!seg2) return DEFAULT_SECTION[module] ?? null;
  const map = SECTIONS[module] ?? {};
  return map[`${seg2}/${seg3}`] ?? map[seg2] ?? DEFAULT_SECTION[module] ?? null;
}

export function RouteBreadcrumb() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const doc = useDocumentCrumb();
  const [, seg1 = "", seg2 = "", seg3 = ""] = pathname.split("/");

  if (!MODULE_SET.has(seg1)) return null;

  const section = sectionKey(seg1, seg2, seg3);
  // On a detail page the document number is the current crumb, so the section steps back to a link
  // to its list (e.g. Sales › Orders › SO-2026-000007, where "Orders" returns to the list).
  const sectionTo = seg2 ? `/${seg1}/${seg2}` : `/${seg1}`;

  return (
    <nav className="crumb" aria-label={t("common.breadcrumb")}>
      <Link to={`/${seg1}`} className="crumb__module">
        <span className="crumb__icon">
          <NavIcon name={seg1} />
        </span>
        <span>{t(`nav.${seg1}`)}</span>
      </Link>
      {section && (
        <>
          <Chevron />
          {doc ? (
            <Link to={sectionTo} className="crumb__link">
              {t(section)}
            </Link>
          ) : (
            <span className="crumb__current">{t(section)}</span>
          )}
        </>
      )}
      {doc && (
        <>
          <Chevron />
          <span className="crumb__current latin">{doc}</span>
        </>
      )}
    </nav>
  );
}
