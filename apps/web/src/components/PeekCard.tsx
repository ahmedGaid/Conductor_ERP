import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { listCustomers, type Customer, type SalesOrder } from "../api/sales";
import { listSuppliers, type Supplier, type PurchaseOrder } from "../api/purchasing";
import { getItem, type ItemDetail } from "../api/inventory";
import { readCache, writeCache } from "../lib/cache";
import { formatMinor } from "../lib/money";
import { NavIcon } from "../app/icons";
import { Popover } from "./Popover";
import { Bdi } from "./Bdi";
import "./PeekCard.css";

/*
 * Peek panels — a small hover/space preview card for the entity a link points at, so a name in a
 * table answers "who/what is this?" without a page load. Only the three types whose detail data is
 * already warmed by hover-prefetch (customer/supplier list, item detail) peek; orders/journals open
 * directly (their id isn't resolved until navigation). The card reads the SAME cache the prefetch
 * fills — no second fetch when warm; a cold hover loads once and shows the shared skeleton meanwhile.
 * One shared card instance lives at the app root (PeekProvider) and is opened via context, so a
 * link (EntityLink) and the list keyboard layer both drive the same floating panel.
 */
export type PeekType = "customer" | "supplier" | "item";
const PEEKABLE = new Set<string>(["customer", "supplier", "item"]);
export function isPeekable(type: string): type is PeekType {
  return PEEKABLE.has(type);
}

// A single fact row. Money/quantity is a pre-formatted string (`value`); a word that must translate
// (a status) is a key (`valueKey`) — so the builders stay pure and locale-agnostic.
type Tone = "warn" | "muted";
interface Fact {
  labelKey: string;
  value?: string;
  valueKey?: string;
  tone?: Tone;
}
interface Peeked {
  icon: string;
  title: string;
  facts: Fact[];
}

function formatQty(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 3 });
}

function customerPeek(code: string): Peeked | null {
  const c = readCache<Customer[]>("sales:customers")?.find((x) => x.code === code);
  if (!c) return null;
  const facts: Fact[] = [
    c.credit_limit_minor
      ? { labelKey: "sales.customer.creditLimit", value: formatMinor(c.credit_limit_minor) }
      : { labelKey: "sales.customer.creditLimit", valueKey: "sales.customer.unlimited", tone: "muted" },
  ];
  const orders = readCache<SalesOrder[]>("sales:orders");
  if (orders) {
    const mine = orders.filter((o) => o.customer_code === code);
    const owed = mine.reduce((s, o) => s + o.outstanding_minor, 0);
    facts.push({ labelKey: "peek.outstanding", value: formatMinor(owed), tone: owed > 0 ? "warn" : undefined });
    facts.push({ labelKey: "peek.orders", value: String(mine.length) });
  }
  if (!c.is_active) facts.push({ labelKey: "peek.status", valueKey: "peek.inactive", tone: "muted" });
  return { icon: "sales", title: c.name, facts };
}

function supplierPeek(code: string): Peeked | null {
  const s = readCache<Supplier[]>("purchasing:suppliers")?.find((x) => x.code === code);
  if (!s) return null;
  const facts: Fact[] = [];
  const pos = readCache<PurchaseOrder[]>("purchasing:orders");
  if (pos) {
    const mine = pos.filter((o) => o.supplier_code === code);
    const owed = mine.reduce((sum, o) => sum + o.outstanding_minor, 0);
    const open = mine.filter((o) => !["received", "paid", "cancelled"].includes(o.status)).length;
    facts.push({ labelKey: "peek.outstanding", value: formatMinor(owed), tone: owed > 0 ? "warn" : undefined });
    facts.push({ labelKey: "peek.openOrders", value: String(open) });
  }
  facts.push({ labelKey: "peek.status", valueKey: s.is_active ? "peek.active" : "peek.inactive", tone: "muted" });
  return { icon: "purchasing", title: s.name, facts };
}

function itemPeek(sku: string): Peeked | null {
  const d = readCache<ItemDetail>(`inventory:item:${sku}`);
  if (!d) return null;
  const onHand = d.stock.rows.reduce((s, r) => s + Number(r.quantity || 0), 0);
  const reorder = Number(d.item.reorder_point || 0);
  const below = d.stock.rows.some((r) => r.below_reorder) || (reorder > 0 && onHand < reorder);
  const facts: Fact[] = [
    { labelKey: "peek.onHand", value: `${formatQty(onHand)} ${d.item.uom}` },
    { labelKey: "peek.stockValue", value: formatMinor(d.stock.total_value_minor) },
    { labelKey: "peek.stockState", valueKey: below ? "peek.belowReorder" : "peek.inStock", tone: below ? "warn" : undefined },
  ];
  return { icon: "inventory", title: d.item.name, facts };
}

function buildPeek(type: PeekType, value: string): Peeked | null {
  if (type === "customer") return customerPeek(value);
  if (type === "supplier") return supplierPeek(value);
  return itemPeek(value);
}

// Cold path: load the one cache the peek reads (mirrors EntityLink's prefetch loaders), so a hover
// that beat the prefetch — or a keyboard peek — still fills in rather than staying blank.
async function warmPeek(type: PeekType, value: string): Promise<void> {
  if (type === "customer") {
    if (!readCache("sales:customers")) writeCache("sales:customers", await listCustomers());
  } else if (type === "supplier") {
    if (!readCache("purchasing:suppliers")) writeCache("purchasing:suppliers", await listSuppliers());
  } else {
    const key = `inventory:item:${value}`;
    if (!readCache(key)) writeCache(key, await getItem(value));
  }
}

interface PeekApi {
  /** Open the shared card for a link's entity, anchored beneath `anchor`. No-op for non-peek types. */
  openPeek: (type: string, value: string, anchor: HTMLElement) => void;
  /** Close after a short grace (mouse left a link — it may be heading for the card). */
  scheduleClose: () => void;
  /** Keep the card open (pointer entered the card, or re-entered the link). */
  cancelClose: () => void;
  /** Close now (route change, click-through, Escape). */
  closePeek: () => void;
  isOpen: boolean;
}

const noop = () => {};
const PeekContext = createContext<PeekApi>({
  openPeek: noop,
  scheduleClose: noop,
  cancelClose: noop,
  closePeek: noop,
  isOpen: false,
});
export function usePeek(): PeekApi {
  return useContext(PeekContext);
}

const CLOSE_GRACE_MS = 140;

interface OpenState {
  type: PeekType;
  value: string;
}

export function PeekProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<OpenState | null>(null);
  const anchorRef = useRef<HTMLElement | null>(null);
  const closeTimer = useRef<number | undefined>(undefined);
  const location = useLocation();

  const cancelClose = useCallback(() => {
    if (closeTimer.current !== undefined) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = undefined;
    }
  }, []);

  const closePeek = useCallback(() => {
    cancelClose();
    anchorRef.current = null;
    setState(null);
  }, [cancelClose]);

  const scheduleClose = useCallback(() => {
    cancelClose();
    closeTimer.current = window.setTimeout(() => setState(null), CLOSE_GRACE_MS);
  }, [cancelClose]);

  const openPeek = useCallback(
    (type: string, value: string, anchor: HTMLElement) => {
      if (!isPeekable(type) || !value) return;
      cancelClose();
      anchorRef.current = anchor;
      setState({ type, value });
    },
    [cancelClose],
  );

  // A route change dismisses a floating peek — it belongs to the page it was opened from.
  useEffect(() => {
    closePeek();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  const api = useMemo<PeekApi>(
    () => ({ openPeek, scheduleClose, cancelClose, closePeek, isOpen: state !== null }),
    [openPeek, scheduleClose, cancelClose, closePeek, state],
  );

  return (
    <PeekContext.Provider value={api}>
      {children}
      <Popover open={state !== null} onClose={closePeek} anchorRef={anchorRef} className="peek-popover">
        {state && (
          <PeekBody
            type={state.type}
            value={state.value}
            onPointerEnter={cancelClose}
            onPointerLeave={scheduleClose}
          />
        )}
      </Popover>
    </PeekContext.Provider>
  );
}

function PeekBody({
  type,
  value,
  onPointerEnter,
  onPointerLeave,
}: {
  type: PeekType;
  value: string;
  onPointerEnter: () => void;
  onPointerLeave: () => void;
}) {
  const { t } = useTranslation();
  const [, force] = useReducer((n: number) => n + 1, 0);

  // If the cache is cold, load it once and re-render when it lands (the warm case returns early).
  useEffect(() => {
    if (buildPeek(type, value)) return;
    let cancelled = false;
    warmPeek(type, value)
      .then(() => {
        if (!cancelled) force();
      })
      .catch(() => {
        /* speculative — a real navigation surfaces any error */
      });
    return () => {
      cancelled = true;
    };
  }, [type, value]);

  const data = buildPeek(type, value);

  return (
    <div className="peek" onPointerEnter={onPointerEnter} onPointerLeave={onPointerLeave}>
      {data ? (
        <>
          <div className="peek__head">
            <span className="peek__icon">
              <NavIcon name={data.icon} />
            </span>
            <span className="peek__title">{data.title}</span>
          </div>
          <dl className="peek__facts">
            {data.facts.map((f, i) => (
              <div className="peek__fact" key={i}>
                <dt className="peek__label">{t(f.labelKey)}</dt>
                <dd className={f.tone ? `peek__value peek__value--${f.tone}` : "peek__value"}>
                  <Bdi>{f.valueKey ? t(f.valueKey) : f.value}</Bdi>
                </dd>
              </div>
            ))}
          </dl>
          <span className="peek__open">
            {t("peek.open")}
            <NavIcon name="expand" />
          </span>
        </>
      ) : (
        <div className="peek__loading" aria-busy="true">
          <span className="visually-hidden">{t("common.loading")}</span>
          <span className="skeleton peek__skeleton" />
          <span className="skeleton peek__skeleton peek__skeleton--sm" />
        </div>
      )}
    </div>
  );
}
