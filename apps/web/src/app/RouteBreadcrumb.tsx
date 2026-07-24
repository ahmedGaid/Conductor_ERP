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
 * Route-driven breadcrumb shown above EVERY page in the app. Identity is icon +
 * place: [module glyph] Module › Section. Monochrome; the module's colour reaches
 * it only through the inherited --color-accent on hover. The section label reuses
 * the module's existing tab labels, so it always matches the nav.
 */

const MODULE_SET = new Set([
  "dashboard",
  "sales",
  "purchasing",
  "inventory",
  "accounting",
  "crm",
  "settings",
  "admin",
  "pricing",
  "workflows",
  "einvoice",
  "assistant",
  "notifications",
  "imports",
  "help",
]);

// A module whose NavIcon glyph name or nav.* label key doesn't match its URL segment.
// Everything not listed here uses NavIcon name={seg1} + t(`nav.${seg1}`) directly.
const MODULE_ICON: Record<string, string> = {
  admin: "settings",
  help: "knowledge",
  assistant: "sparkle",
  imports: "import",
};
const MODULE_LABEL: Record<string, string> = {
  admin: "nav.administration",
  help: "shell.userGuide",
};
// admin has no bare "/admin" route (it starts at /admin/users) — send its module chip there
// instead of a dead link that would bounce to the dashboard via the "*" fallback.
const MODULE_HOME: Record<string, string> = {
  admin: "/admin/users",
};

// Landing section for each module's bare "/module" route. A module absent here either has
// no bare route (admin) or its bare route is the whole page with no sub-section (einvoice,
// assistant, notifications, imports, settings — settings redirects instantly, imports' bare
// route is the history list, both fine as chip-only).
const DEFAULT_SECTION: Record<string, string> = {
  sales: "sales.tabs.orders",
  purchasing: "purchasing.tabs.orders",
  inventory: "inventory.tabs.stockOnHand",
  accounting: "accounting.tabs.chart",
  crm: "crm.tabs.pipeline",
  pricing: "pricing.tabs.lists",
  workflows: "automations.title",
};

// Modules whose entire catalogue lives at the bare "/module" route, so a detail id sits
// directly at the seg2 position with no literal path token (e.g. "/pricing/:id",
// "/crm/opportunities/:id" — "opportunities" isn't a SECTIONS key). An unmatched seg2 here
// IS a detail page of that bare list — fall back to its section label, link back to it.
// Every other module leaves an unmatched seg2 chip-only (safer than guessing a wrong label).
const ROOT_DETAIL_MODULES = new Set(["crm", "pricing"]);

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
    "orders/import": "purchasing.tabs.importInvoice",
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
  settings: {
    profile: "settings.tabs.profile",
    appearance: "settings.tabs.appearance",
    dashboard: "settings.tabs.dashboard",
    navigation: "settings.tabs.navigation",
    notifications: "settings.tabs.notifications",
    accessibility: "settings.tabs.accessibility",
    organization: "settings.tabs.organization",
    branches: "settings.tabs.branches",
    webhooks: "settings.tabs.webhooks",
    "custom-fields": "settings.tabs.customFields",
    developers: "settings.tabs.developers",
    einvoice: "settings.tabs.einvoice",
    system: "settings.tabs.system",
    "ai-usage": "settings.tabs.aiUsage",
  },
  admin: {
    users: "nav.usersAdmin",
    roles: "nav.rolesAdmin",
  },
  pricing: {
    customers: "pricing.tabs.customers",
  },
  workflows: {
    advanced: "workflow.tabs.workflows",
    instances: "workflow.tabs.instances",
    templates: "automations.title",
    build: "automations.startFromScratch",
  },
  assistant: {
    knowledge: "nav.knowledgeAdmin",
    ops: "nav.opsAdmin",
  },
};

// Sections whose list lives at the bare "/module" route (the module's default landing) — there is
// no "/module/seg2" route for them, so a detail page must step back to "/module". Linking to
// "/module/seg2" would hit the "*" fallback and bounce to the dashboard. Every other section has
// its own "/module/seg2" list route, so it steps back there normally.
const BARE_LIST_SECTION: Record<string, string> = {
  sales: "orders",
  purchasing: "orders",
  crm: "opportunities",
};

// Resolves both the section label and where its crumb links back to, in one place, so the two
// can never drift out of sync (see ROOT_DETAIL_MODULES above for the "id sits directly at seg2"
// case that needs its own fallback path).
function resolveSection(module: string, seg2: string, seg3: string): { label: string | null; to: string } {
  const bare = `/${module}`;
  if (!seg2) return { label: DEFAULT_SECTION[module] ?? null, to: bare };
  const map = SECTIONS[module] ?? {};
  const composite = map[`${seg2}/${seg3}`];
  const literal = composite ?? map[seg2];
  if (literal !== undefined) {
    return { label: literal, to: BARE_LIST_SECTION[module] === seg2 ? bare : `${bare}/${seg2}` };
  }
  if (ROOT_DETAIL_MODULES.has(module)) return { label: DEFAULT_SECTION[module] ?? null, to: bare };
  return { label: null, to: bare };
}

export function RouteBreadcrumb() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const doc = useDocumentCrumb();
  let [, seg1 = "", seg2 = "", seg3 = ""] = pathname.split("/");
  // "/instances/:id" (ExecutionViewerPage) is a workflow run detail page living at its own
  // top-level route (no "/workflows" prefix) — fold it back into the workflows module so it gets
  // "Workflows › Runs › <id>" instead of a blank crumb for an unknown "instances" module.
  if (seg1 === "instances") {
    seg1 = "workflows";
    seg2 = "instances";
    seg3 = "";
  }
  // The home dashboard lives at bare "/" (no seg1 at all) — give it its own module identity so it
  // gets a (chip-only, no section) crumb like every other page instead of being a special case.
  if (pathname === "/") seg1 = "dashboard";

  if (!MODULE_SET.has(seg1)) return null;

  const { label: section, to: sectionTo } = resolveSection(seg1, seg2, seg3);
  const moduleHref = seg1 === "dashboard" ? "/" : (MODULE_HOME[seg1] ?? `/${seg1}`);

  return (
    <nav className="crumb" aria-label={t("common.breadcrumb")}>
      <Link to={moduleHref} className="crumb__module">
        <span className="crumb__icon">
          <NavIcon name={MODULE_ICON[seg1] ?? seg1} />
        </span>
        <span>{t(MODULE_LABEL[seg1] ?? `nav.${seg1}`)}</span>
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
