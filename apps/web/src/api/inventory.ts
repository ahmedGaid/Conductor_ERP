// Typed wrappers for the inventory API (/api/inventory/*).
// Quantities are decimal strings; costs/values are integer minor units.
import { apiFetch } from "./client";

export type ItemType = "stock" | "service";
export type MovementType = "receipt" | "issue" | "transfer";

export interface Item {
  id: string;
  sku: string;
  name: string;
  category_code: string | null;
  uom: string;
  type: ItemType;
  is_active: boolean;
  reorder_point: string;
}

export interface Warehouse {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface Movement {
  id: string;
  type: MovementType;
  item_sku: string;
  warehouse_code: string;
  dest_warehouse_code: string | null;
  date: string;
  quantity: string;
  unit_cost_minor: number;
  value_minor: number;
  reference: string;
  memo: string;
  journal_number: string;
}

export interface BalanceRow {
  sku: string;
  item_name: string;
  warehouse_code: string;
  quantity: string;
  avg_cost_minor: number;
  value_minor: number;
  below_reorder: boolean;
}

export interface StockOnHand {
  rows: BalanceRow[];
  total_value_minor: number;
}

export function listItems(): Promise<Item[]> {
  return apiFetch<Item[]>("/inventory/items");
}

export function createItem(payload: {
  sku: string;
  name: string;
  uom?: string;
  type?: ItemType;
  reorder_point?: string;
}): Promise<Item> {
  return apiFetch<Item>("/inventory/items", { method: "POST", body: JSON.stringify(payload) });
}

export function listWarehouses(): Promise<Warehouse[]> {
  return apiFetch<Warehouse[]>("/inventory/warehouses");
}

export function createWarehouse(payload: { code: string; name: string }): Promise<Warehouse> {
  return apiFetch<Warehouse>("/inventory/warehouses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listMovements(item?: string): Promise<Movement[]> {
  const qs = item ? `?item=${encodeURIComponent(item)}` : "";
  return apiFetch<Movement[]>(`/inventory/movements${qs}`);
}

export function receiveStock(payload: {
  item_sku: string;
  warehouse_code: string;
  quantity: string;
  unit_cost: number;
  date?: string;
  reference?: string;
  memo?: string;
}): Promise<Movement> {
  return apiFetch<Movement>("/inventory/movements/receive", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function issueStock(payload: {
  item_sku: string;
  warehouse_code: string;
  quantity: string;
  date?: string;
  reference?: string;
  memo?: string;
}): Promise<Movement> {
  return apiFetch<Movement>("/inventory/movements/issue", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function transferStock(payload: {
  item_sku: string;
  source_code: string;
  dest_code: string;
  quantity: string;
  date?: string;
  reference?: string;
  memo?: string;
}): Promise<Movement> {
  return apiFetch<Movement>("/inventory/movements/transfer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function stockOnHand(): Promise<StockOnHand> {
  return apiFetch<StockOnHand>("/inventory/reports/stock-on-hand");
}
