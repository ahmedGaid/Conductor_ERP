// Typed wrappers for the inventory API (/api/inventory/*).
// Quantities are decimal strings; costs/values are integer minor units.
import { apiFetch } from "./client";

export type ItemType = "stock" | "service";
export type MovementType = "receipt" | "issue" | "transfer" | "return_in" | "return_out" | "adjustment";
export type CountStatus = "counting" | "posted" | "cancelled";

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
  batch_no: string;
  expiry_date: string | null;
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

export interface ItemDetail {
  item: Item;
  stock: StockOnHand;
  movements: Movement[];
}

export function getItem(sku: string): Promise<ItemDetail> {
  return apiFetch<ItemDetail>(`/inventory/items/${encodeURIComponent(sku)}`);
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

export interface WarehouseDetail {
  warehouse: Warehouse;
  stock: StockOnHand;
  movements: Movement[];
}

export function getWarehouse(code: string): Promise<WarehouseDetail> {
  return apiFetch<WarehouseDetail>(`/inventory/warehouses/${encodeURIComponent(code)}`);
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
  batch_no?: string;
  expiry_date?: string | null;
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

// ---- Stock counts ----

export interface StockCountLine {
  id: string;
  item_sku: string;
  item_name: string;
  system_quantity: string;
  counted_quantity: string | null;
  variance_quantity: string;
  variance_value_minor: number;
}

export interface StockCount {
  id: string;
  warehouse_code: string;
  count_date: string;
  reference: string;
  memo: string;
  status: CountStatus;
  line_count: number;
  lines?: StockCountLine[];
}

export function listStockCounts(): Promise<StockCount[]> {
  return apiFetch<StockCount[]>("/inventory/counts");
}

export function getStockCount(id: string): Promise<StockCount> {
  return apiFetch<StockCount>(`/inventory/counts/${id}`);
}

export function createStockCount(payload: {
  warehouse_code: string;
  count_date?: string;
  reference?: string;
  item_skus?: string[];
}): Promise<StockCount> {
  return apiFetch<StockCount>("/inventory/counts", { method: "POST", body: JSON.stringify(payload) });
}

export function setCountLine(lineId: string, counted_quantity: string): Promise<StockCount> {
  return apiFetch<StockCount>(`/inventory/count-lines/${lineId}/set`, {
    method: "POST",
    body: JSON.stringify({ counted_quantity }),
  });
}

export function postStockCount(id: string): Promise<StockCount> {
  return apiFetch<StockCount>(`/inventory/counts/${id}/post`, { method: "POST", body: "{}" });
}

// ---- Batches / lots ----

export interface BatchRow {
  batch_no: string;
  sku: string;
  item_name: string;
  warehouse_code: string;
  received_quantity: string;
  earliest_expiry: string | null;
}

export function listBatches(): Promise<BatchRow[]> {
  return apiFetch<BatchRow[]>("/inventory/reports/batches");
}
