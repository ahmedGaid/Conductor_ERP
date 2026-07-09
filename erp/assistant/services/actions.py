"""Write actions the assistant may PROPOSE. Nothing here executes from model output alone.

Flow: the agent loop emits a proposal → the user sees a card (summary, records, risks) → an explicit
confirm → ``execute()`` runs the module contract **as the actor** → ``audit.record`` → a result card
with links. The model shapes the payload; only a human click spends it. Drafts only — nothing the
assistant creates is posted/approved; posting stays on the normal module screens.

Two safety boundaries, both mirroring the read tools:
- **Permission** — ``build_proposal`` and ``execute`` both check the actor's role, so a user who
  cannot create the document gets the calm refusal at proposal time, never a card they can't use.
- **Validation without writing** — ``build_proposal`` resolves every code, prices the lines and
  totals in minor units, so the card shows real numbers and real record links before anything exists.
  ``execute`` re-runs the same resolution against the persisted payload, so a stale proposal can never
  create the wrong thing.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Callable

from erp.identity.roles import BRANCH_MANAGER, SYSTEM_ADMIN
from erp.inventory import contracts as inventory
from erp.pricing import contracts as pricing
from erp.purchasing import contracts as purchasing
from erp.sales import contracts as sales


def _egp(minor: int | None) -> str:
    """Integer minor units → a human EGP string (money formats at the edge, mirrors tools._egp)."""
    return f"{(minor or 0) / 100:,.2f} EGP"


def _lines_total(lines: list[dict]) -> int:
    """Sum a list of ``{quantity, unit_price_minor}`` dicts — used for a before/after diff line."""
    return sum(int((Decimal(ln["quantity"]) * Decimal(ln["unit_price_minor"])).quantize(Decimal("1")))
               for ln in lines)


def _can(actor, *roles: str) -> bool:
    """Role gate mirroring ``HasAnyRole`` — superuser / System Admin bypass, else any of ``roles``."""
    if not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    held = set(actor.roles)
    return SYSTEM_ADMIN in held or bool(held.intersection(roles))


def _refused() -> dict:
    """The one blame-free refusal used when the actor's role can't create the document."""
    return {"error": "You do not have permission to create this document."}


def _blocker(entity: str, query, *, kind: str = "missing", candidates: list | None = None) -> dict:
    """A dependency-shaped failure — the record the request leans on is missing / inactive /
    ambiguous. The loop turns this into an actionable suggestion (session 12): issue → fastest
    permitted fix → resume. Plain failures (permission, validation) keep the string convention."""
    block: dict = {"kind": "ambiguous" if candidates else kind, "entity": entity,
                   "query": str(query or "").strip()}
    if candidates:
        block["candidates"] = candidates
    return {"blocker": block}


def _resolve_warehouse(warehouse: str | None) -> tuple[str, dict | None]:
    """An explicit code is validated (unknown → missing, disabled → inactive blocker); blank falls
    back to the default warehouse, or a missing-warehouse blocker when none is configured yet."""
    code = (warehouse or "").strip()
    if code:
        info = inventory.find_warehouse(code)
        if info is None:
            return "", _blocker("warehouse", code)
        if not info.is_active:
            return "", _blocker("warehouse", code, kind="inactive")
        return info.code, None
    default = inventory.default_warehouse_code()
    if not default:
        return "", _blocker("warehouse", "")
    return default, None


def _qty(value) -> Decimal | None:
    try:
        q = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return q if q > 0 else None


# --- record resolution (fuzzy, mirrors extraction's matcher) ------------------------------------

def _rank(name: str, candidates: list, key) -> list[tuple[float, object]]:
    target = (name or "").casefold().strip()
    scored = [(SequenceMatcher(None, target, (key(c) or "").casefold().strip()).ratio(), c)
              for c in candidates]
    return sorted(scored, key=lambda pair: pair[0], reverse=True)


def _resolve_item(query: str) -> inventory.ItemInfo | None:
    """A stock item query → one ItemInfo: exact SKU wins, else the best name match (≥0.6)."""
    q = (query or "").strip()
    if not q:
        return None
    exact = inventory.find_item(q)
    if exact is not None and exact.type == "stock" and exact.is_active:
        return exact
    ranked = _rank(q, inventory.list_items(), lambda i: i.name)
    if ranked and ranked[0][0] >= 0.6:
        return ranked[0][1]
    return None


# --- Action 1: sales order draft ----------------------------------------------------------------

def _build_sales_order(actor, *, customer: str | None = None, items=None,
                       warehouse: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    snapshot = sales.customer_profile(actor, query=(customer or ""))
    profile = snapshot.get("customer")
    if profile is None:
        near = [{"code": c["code"], "name": c["name"], "score": round(score, 2)}
                for score, c in _rank(customer or "", sales.find_customers(actor, query="", limit=100),
                                      lambda c: c["name"]) if score >= 0.4][:3]
        return _blocker("customer", customer, candidates=near)
    warehouse_code, blocked = _resolve_warehouse(warehouse)
    if blocked is not None:
        return blocked

    lines, records, risks = [], [], []
    unresolved: list[str] = []
    total = 0
    for entry in items or []:
        item = _resolve_item(entry.get("item") if isinstance(entry, dict) else None)
        qty = _qty(entry.get("quantity") if isinstance(entry, dict) else None)
        if item is None:
            unresolved.append(str((entry or {}).get("item", "") if isinstance(entry, dict) else ""))
            risks.append(f"Item '{unresolved[-1]}' was not found — skipped.")
            continue
        if qty is None:
            risks.append(f"'{item.name}' had no valid quantity — skipped.")
            continue
        price = pricing.resolve_unit_price(profile["code"], item.sku, quantity=qty)
        unit = price.unit_price_minor if price is not None else 0
        if price is None:
            risks.append(f"No price on file for '{item.name}' — set it on the order screen.")
        line_total = int((qty * Decimal(unit)).quantize(Decimal("1")))
        total += line_total
        lines.append({"item_sku": item.sku, "quantity": str(qty), "unit_price_minor": unit,
                      "description": item.name})
        records.append({"type": "item", "value": item.sku, "label": item.name})
    if not lines:
        if unresolved and unresolved[0]:
            near = [{"code": i.sku, "name": i.name, "score": round(score, 2)}
                    for score, i in _rank(unresolved[0], inventory.list_items(), lambda i: i.name)
                    if score >= 0.4][:3]
            return _blocker("item", unresolved[0], candidates=near)
        return {"error": "None of the requested items could be added."}

    # Overdue balance is a risk line on the card, never a block (the human decides).
    owed = snapshot.get("outstanding_minor", 0)
    if owed and owed > 0:
        risks.append(f"{profile['name']} still owes {_egp(owed)}.")

    records.insert(0, {"type": "customer", "value": profile["code"], "label": profile["name"]})
    return {
        "action": "create_sales_order_draft",
        "summary": [
            f"Draft sales order for {profile['name']}",
            f"{len(lines)} line(s), total {_egp(total)}",
        ],
        "records": records,
        "risks": risks,
        "total": _egp(total),
        "affected": len(records),
        "payload": {"customer_code": profile["code"], "warehouse_code": warehouse_code,
                    "lines": lines},
    }


def _execute_sales_order(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    order = sales.place_order(
        customer_code=payload["customer_code"], warehouse_code=payload["warehouse_code"],
        lines=[sales.OrderLineInput(item_sku=ln["item_sku"], quantity=Decimal(ln["quantity"]),
                                    unit_price_minor=ln["unit_price_minor"],
                                    description=ln.get("description", "")) for ln in payload["lines"]],
        actor=actor,
    )
    if order is None:
        raise ValueError("customer no longer exists")
    return {
        "summary": f"Draft sales order {order.number} created.",
        "links": [{"type": "order", "value": str(order.id), "label": order.number}],
    }


# --- Action 2: purchase request draft -----------------------------------------------------------

def _build_purchase_request(actor, *, supplier: str | None = None, items=None,
                            warehouse: str | None = None, from_low_stock=None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    # No supplier at all is a missing INPUT, not a missing RECORD — a blocker card offering to
    # "create the supplier \"\"" would be nonsense. Same for an empty item list below.
    if not (supplier or "").strip():
        return {"error": "No supplier was given. Ask the user which supplier this request is for."}
    if not from_low_stock and not list(items or []):
        return {"error": "No items were given. Ask the user which items and quantities to request."}
    ranked = _rank(supplier or "", purchasing.list_suppliers(), lambda s: s.name) if supplier else []
    match = ranked[0][1] if ranked and ranked[0][0] >= 0.6 else None
    if match is None:
        near = [{"code": s.code, "name": s.name, "score": round(score, 2)}
                for score, s in ranked if score >= 0.4][:3]
        return _blocker("supplier", supplier, candidates=near)

    entries = list(items or [])
    warehouse_code = ""
    if (warehouse or "").strip():
        warehouse_code, blocked = _resolve_warehouse(warehouse)
        if blocked is not None:
            return blocked
    risks = []
    if from_low_stock:
        low = inventory.low_stock(limit=20)
        if not low:
            return {"error": "Nothing is below its reorder point right now."}
        entries = [{"item": r["sku"], "quantity": "1"} for r in low]
        warehouse_code = warehouse_code or (low[0].get("warehouse_code") or "")
        risks.append("Quantities defaulted to 1 — set the real amounts on the request screen.")
    if not warehouse_code:
        warehouse_code, blocked = _resolve_warehouse("")
        if blocked is not None:
            return blocked

    lines, records = [], []
    unresolved: list[str] = []
    total = 0
    for entry in entries:
        item = _resolve_item(entry.get("item") if isinstance(entry, dict) else None)
        qty = _qty(entry.get("quantity") if isinstance(entry, dict) else None)
        if item is None:
            unresolved.append(str((entry or {}).get("item", "") if isinstance(entry, dict) else ""))
            risks.append(f"Item '{unresolved[-1]}' was not found — skipped.")
            continue
        if qty is None:
            risks.append(f"'{item.name}' had no valid quantity — skipped.")
            continue
        raw_cost = entry.get("unit_cost") if isinstance(entry, dict) else None
        cost = int(raw_cost) if isinstance(raw_cost, (int, float)) and raw_cost > 0 else 0
        if cost == 0:
            risks.append(f"No cost given for '{item.name}' — set it on the request screen.")
        line_total = int((qty * Decimal(cost)).quantize(Decimal("1")))
        total += line_total
        lines.append({"item_sku": item.sku, "quantity": str(qty), "unit_cost_minor": cost,
                      "description": item.name})
        records.append({"type": "item", "value": item.sku, "label": item.name})
    if not lines:
        if unresolved and unresolved[0]:
            near = [{"code": i.sku, "name": i.name, "score": round(score, 2)}
                    for score, i in _rank(unresolved[0], inventory.list_items(), lambda i: i.name)
                    if score >= 0.4][:3]
            return _blocker("item", unresolved[0], candidates=near)
        return {"error": "None of the requested items could be added."}

    records.insert(0, {"type": "supplier", "value": match.code, "label": match.name})
    return {
        "action": "create_purchase_request_draft",
        "summary": [
            f"Draft purchase request to {match.name}",
            f"{len(lines)} line(s), estimated {_egp(total)}",
        ],
        "records": records,
        "risks": risks,
        "total": _egp(total),
        "affected": len(records),
        "payload": {"supplier_code": match.code, "warehouse_code": warehouse_code, "lines": lines},
    }


def _execute_purchase_request(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    req = purchasing.place_request(
        supplier_code=payload["supplier_code"], warehouse_code=payload["warehouse_code"],
        lines=[purchasing.RequestLineInput(item_sku=ln["item_sku"], quantity=Decimal(ln["quantity"]),
                                           unit_cost_minor=ln["unit_cost_minor"],
                                           description=ln.get("description", ""))
               for ln in payload["lines"]],
        actor=actor,
    )
    if req is None:
        raise ValueError("supplier no longer exists")
    return {
        "summary": f"Draft purchase request {req.number} created.",
        "links": [{"type": "purchaseRequest", "value": str(req.id), "label": req.number}],
    }


# --- Action 3: create customer ------------------------------------------------------------------

def _build_customer(actor, *, query: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    name = (query or "").strip()
    if not name:
        return {"error": "What name should the new customer have?"}
    risks = []
    # Fuzzy duplicate check against the actor's customers: an exact-name match blocks (never a silent
    # second record); a close-but-not-equal match is a risk line the user can override.
    everyone = sales.find_customers(actor, query="", limit=100)
    target = name.casefold().strip()
    exact = next((c for c in everyone if (c["name"] or "").casefold().strip() == target), None)
    if exact is not None:
        return {"error": f"A customer named '{exact['name']}' ({exact['code']}) already exists."}
    near = [c for score, c in _rank(name, everyone, lambda c: c["name"]) if score >= 0.7][:3]
    if near:
        joined = ", ".join(f"{c['name']} ({c['code']})" for c in near)
        risks.append(f"Similar customers already exist: {joined}.")
    return {
        "action": "create_customer",
        "summary": [f"New customer '{name}'"],
        "records": [],
        "risks": risks,
        "total": None,
        "affected": 1,
        "payload": {"name": name},
    }


def _execute_customer(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    info = sales.create_customer(name=payload["name"], actor=actor)
    return {
        "summary": f"Customer {info.name} ({info.code}) created.",
        "links": [{"type": "customer", "value": info.code, "label": info.name}],
    }


# --- Action 4: quotation draft ------------------------------------------------------------------

def _build_quotation(actor, *, customer: str | None = None, items=None,
                     warehouse: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    snapshot = sales.customer_profile(actor, query=(customer or ""))
    profile = snapshot.get("customer")
    if profile is None:
        near = [{"code": c["code"], "name": c["name"], "score": round(score, 2)}
                for score, c in _rank(customer or "", sales.find_customers(actor, query="", limit=100),
                                      lambda c: c["name"]) if score >= 0.4][:3]
        return _blocker("customer", customer, candidates=near)
    warehouse_code, blocked = _resolve_warehouse(warehouse)
    if blocked is not None:
        return blocked

    lines, records, risks = [], [], []
    unresolved: list[str] = []
    total = 0
    for entry in items or []:
        item = _resolve_item(entry.get("item") if isinstance(entry, dict) else None)
        qty = _qty(entry.get("quantity") if isinstance(entry, dict) else None)
        if item is None:
            unresolved.append(str((entry or {}).get("item", "") if isinstance(entry, dict) else ""))
            risks.append(f"Item '{unresolved[-1]}' was not found — skipped.")
            continue
        if qty is None:
            risks.append(f"'{item.name}' had no valid quantity — skipped.")
            continue
        price = pricing.resolve_unit_price(profile["code"], item.sku, quantity=qty)
        unit = price.unit_price_minor if price is not None else 0
        if price is None:
            risks.append(f"No price on file for '{item.name}' — set it on the quote screen.")
        line_total = int((qty * Decimal(unit)).quantize(Decimal("1")))
        total += line_total
        lines.append({"item_sku": item.sku, "quantity": str(qty), "unit_price_minor": unit,
                      "description": item.name})
        records.append({"type": "item", "value": item.sku, "label": item.name})
    if not lines:
        if unresolved and unresolved[0]:
            near = [{"code": i.sku, "name": i.name, "score": round(score, 2)}
                    for score, i in _rank(unresolved[0], inventory.list_items(), lambda i: i.name)
                    if score >= 0.4][:3]
            return _blocker("item", unresolved[0], candidates=near)
        return {"error": "None of the requested items could be added."}

    owed = snapshot.get("outstanding_minor", 0)
    if owed and owed > 0:
        risks.append(f"{profile['name']} still owes {_egp(owed)}.")

    records.insert(0, {"type": "customer", "value": profile["code"], "label": profile["name"]})
    return {
        "action": "create_quotation_draft",
        "summary": [
            f"Draft quotation for {profile['name']}",
            f"{len(lines)} line(s), total {_egp(total)}",
        ],
        "records": records,
        "risks": risks,
        "total": _egp(total),
        "affected": len(records),
        "payload": {"customer_code": profile["code"], "warehouse_code": warehouse_code,
                    "lines": lines},
    }


def _execute_quotation(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    quote = sales.place_quotation(
        customer_code=payload["customer_code"], warehouse_code=payload["warehouse_code"],
        lines=[sales.QuoteLineInput(item_sku=ln["item_sku"], quantity=Decimal(ln["quantity"]),
                                    unit_price_minor=ln["unit_price_minor"],
                                    description=ln.get("description", "")) for ln in payload["lines"]],
        actor=actor,
    )
    if quote is None:
        raise ValueError("customer no longer exists")
    return {
        "summary": f"Draft quotation {quote.number} created.",
        "links": [{"type": "quotation", "value": str(quote.id), "label": quote.number}],
    }


# --- Action 5: convert a quotation into a sales order draft --------------------------------------

def _build_convert_quotation(actor, *, query: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    q = (query or "").strip()
    if not q:
        return {"error": "Which quotation? Give its number or the customer's name."}
    matches = sales.find_quotations(actor, query=q, limit=5)
    if not matches:
        return _blocker("quotation", q)
    quote = matches[0]

    risks = []
    if quote["status"] == "converted":
        risks.append(f"Already converted to order {quote['converted_order_number']}.")
    elif quote["status"] != "approved":
        risks.append(f"Quotation is '{quote['status']}', not approved yet — confirming will fail "
                     "until it is approved on the quotation screen.")

    records = [
        {"type": "customer", "value": quote["customer_code"], "label": quote["customer_name"]},
        {"type": "quotation", "value": quote["id"], "label": quote["number"]},
    ]
    return {
        "action": "convert_quotation",
        "summary": [
            f"Convert {quote['number']} ({quote['customer_name']}) into a sales order draft",
            f"{len(quote['lines'])} line(s), total {_egp(quote['subtotal_minor'])}",
        ],
        "records": records,
        "risks": risks,
        "total": _egp(quote["subtotal_minor"]),
        "affected": len(records),
        "payload": {"quotation_number": quote["number"]},
    }


def _execute_convert_quotation(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    order = sales.convert_quotation(payload["quotation_number"], actor=actor)
    if order is None:
        raise ValueError("quotation no longer exists")
    return {
        "summary": f"Quotation converted — sales order {order.number} created.",
        "links": [{"type": "order", "value": str(order.id), "label": order.number}],
    }


# --- Action 6: edit a draft sales order's lines ---------------------------------------------------

def _build_edit_sales_order(actor, *, query: str | None = None, items=None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    q = (query or "").strip()
    if not q:
        return {"error": "Which order? Give its number."}
    order = sales.find_order(actor, query=q)
    if order is None:
        return _blocker("order", q)
    if order["status"] != "draft":
        return {"error": f"Order {order['number']} is '{order['status']}', not a draft — its lines "
                         "can no longer be changed here."}

    lines, records, risks = [], [], []
    unresolved: list[str] = []
    total = 0
    for entry in items or []:
        item = _resolve_item(entry.get("item") if isinstance(entry, dict) else None)
        qty = _qty(entry.get("quantity") if isinstance(entry, dict) else None)
        if item is None:
            unresolved.append(str((entry or {}).get("item", "") if isinstance(entry, dict) else ""))
            risks.append(f"Item '{unresolved[-1]}' was not found — skipped.")
            continue
        if qty is None:
            risks.append(f"'{item.name}' had no valid quantity — skipped.")
            continue
        raw_price = entry.get("unit_price") if isinstance(entry, dict) else None
        if isinstance(raw_price, (int, float)) and raw_price > 0:
            unit = int(raw_price)
        else:
            price = pricing.resolve_unit_price(order["customer_code"], item.sku, quantity=qty)
            unit = price.unit_price_minor if price is not None else 0
            if price is None:
                risks.append(f"No price on file for '{item.name}' — set it on the order screen.")
        line_total = int((qty * Decimal(unit)).quantize(Decimal("1")))
        total += line_total
        lines.append({"item_sku": item.sku, "quantity": str(qty), "unit_price_minor": unit,
                      "description": item.name})
        records.append({"type": "item", "value": item.sku, "label": item.name})
    if not lines:
        if unresolved and unresolved[0]:
            near = [{"code": i.sku, "name": i.name, "score": round(score, 2)}
                    for score, i in _rank(unresolved[0], inventory.list_items(), lambda i: i.name)
                    if score >= 0.4][:3]
            return _blocker("item", unresolved[0], candidates=near)
        return {"error": "None of the requested items could be added."}

    records.insert(0, {"type": "order", "value": order["id"], "label": order["number"]})
    return {
        "action": "edit_sales_order_draft",
        "summary": [
            f"Change draft order {order['number']} to {len(lines)} line(s)",
            f"before {_egp(_lines_total(order['lines']))} → after {_egp(total)}",
        ],
        "records": records,
        "risks": risks,
        "total": _egp(total),
        "affected": len(records),
        "payload": {"order_number": order["number"], "lines": lines},
    }


def _execute_edit_sales_order(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    order = sales.update_draft_order(
        order_number=payload["order_number"],
        lines=[sales.OrderLineInput(item_sku=ln["item_sku"], quantity=Decimal(ln["quantity"]),
                                    unit_price_minor=ln["unit_price_minor"],
                                    description=ln.get("description", "")) for ln in payload["lines"]],
        actor=actor,
    )
    if order is None:
        raise ValueError("order no longer exists")
    return {
        "summary": f"Draft order {order.number} updated.",
        "links": [{"type": "order", "value": str(order.id), "label": order.number}],
    }


# --- Action 7: purchase order draft -------------------------------------------------------------

def _build_purchase_order(actor, *, supplier: str | None = None, items=None,
                          warehouse: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    ranked = _rank(supplier or "", purchasing.list_suppliers(), lambda s: s.name) if supplier else []
    match = ranked[0][1] if ranked and ranked[0][0] >= 0.6 else None
    if match is None:
        near = [{"code": s.code, "name": s.name, "score": round(score, 2)}
                for score, s in ranked if score >= 0.4][:3]
        return _blocker("supplier", supplier, candidates=near)
    warehouse_code, blocked = _resolve_warehouse(warehouse)
    if blocked is not None:
        return blocked

    lines, records, risks = [], [], []
    unresolved: list[str] = []
    total = 0
    for entry in items or []:
        item = _resolve_item(entry.get("item") if isinstance(entry, dict) else None)
        qty = _qty(entry.get("quantity") if isinstance(entry, dict) else None)
        if item is None:
            unresolved.append(str((entry or {}).get("item", "") if isinstance(entry, dict) else ""))
            risks.append(f"Item '{unresolved[-1]}' was not found — skipped.")
            continue
        if qty is None:
            risks.append(f"'{item.name}' had no valid quantity — skipped.")
            continue
        raw_cost = entry.get("unit_cost") if isinstance(entry, dict) else None
        cost = int(raw_cost) if isinstance(raw_cost, (int, float)) and raw_cost > 0 else 0
        if cost == 0:
            risks.append(f"No cost given for '{item.name}' — set it on the order screen.")
        line_total = int((qty * Decimal(cost)).quantize(Decimal("1")))
        total += line_total
        lines.append({"item_sku": item.sku, "quantity": str(qty), "unit_cost_minor": cost,
                      "description": item.name})
        records.append({"type": "item", "value": item.sku, "label": item.name})
    if not lines:
        if unresolved and unresolved[0]:
            near = [{"code": i.sku, "name": i.name, "score": round(score, 2)}
                    for score, i in _rank(unresolved[0], inventory.list_items(), lambda i: i.name)
                    if score >= 0.4][:3]
            return _blocker("item", unresolved[0], candidates=near)
        return {"error": "None of the requested items could be added."}

    records.insert(0, {"type": "supplier", "value": match.code, "label": match.name})
    return {
        "action": "create_purchase_order_draft",
        "summary": [
            f"Draft purchase order to {match.name}",
            f"{len(lines)} line(s), total {_egp(total)}",
        ],
        "records": records,
        "risks": risks,
        "total": _egp(total),
        "affected": len(records),
        "payload": {"supplier_code": match.code, "warehouse_code": warehouse_code, "lines": lines},
    }


def _execute_purchase_order(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    order = purchasing.place_order(
        supplier_code=payload["supplier_code"], warehouse_code=payload["warehouse_code"],
        lines=[purchasing.POLineInput(item_sku=ln["item_sku"], quantity=Decimal(ln["quantity"]),
                                      unit_cost_minor=ln["unit_cost_minor"],
                                      description=ln.get("description", ""))
               for ln in payload["lines"]],
        actor=actor,
    )
    if order is None:
        raise ValueError("supplier no longer exists")
    return {
        "summary": f"Draft purchase order {order.number} created.",
        "links": [{"type": "purchaseOrder", "value": str(order.id), "label": order.number}],
    }


# --- Action 8: convert a purchase request into a purchase order draft ----------------------------

def _build_convert_purchase_request(actor, *, query: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    q = (query or "").strip()
    if not q:
        return {"error": "Which request? Give its number or the supplier's name."}
    matches = purchasing.find_requests(actor, query=q, limit=5)
    if not matches:
        return _blocker("purchase request", q)
    req = matches[0]

    risks = []
    if req["status"] == "converted":
        risks.append(f"Already converted to order {req['converted_order_number']}.")
    elif req["status"] != "approved":
        risks.append(f"Request is '{req['status']}', not approved yet — confirming will fail until "
                     "it is approved on the purchase request screen.")

    records = [
        {"type": "supplier", "value": req["supplier_code"], "label": req["supplier_name"]},
        {"type": "purchaseRequest", "value": req["id"], "label": req["number"]},
    ]
    return {
        "action": "convert_purchase_request",
        "summary": [
            f"Convert {req['number']} ({req['supplier_name']}) into a purchase order draft",
            f"{len(req['lines'])} line(s), total {_egp(req['subtotal_minor'])}",
        ],
        "records": records,
        "risks": risks,
        "total": _egp(req["subtotal_minor"]),
        "affected": len(records),
        "payload": {"request_number": req["number"]},
    }


def _execute_convert_purchase_request(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    order = purchasing.convert_purchase_request(payload["request_number"], actor=actor)
    if order is None:
        raise ValueError("purchase request no longer exists")
    return {
        "summary": f"Purchase request converted — purchase order {order.number} created.",
        "links": [{"type": "purchaseOrder", "value": str(order.id), "label": order.number}],
    }


# --- Action 9: create supplier --------------------------------------------------------------------

def _build_supplier(actor, *, query: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    name = (query or "").strip()
    if not name:
        return {"error": "What name should the new supplier have?"}
    if purchasing.supplier_name_exists(name):
        return {"error": f"A supplier named '{name}' already exists."}
    risks = []
    near = [s for score, s in _rank(name, purchasing.list_suppliers(), lambda s: s.name)
            if score >= 0.7][:3]
    if near:
        joined = ", ".join(f"{s.name} ({s.code})" for s in near)
        risks.append(f"Similar suppliers already exist: {joined}.")
    return {
        "action": "create_supplier",
        "summary": [f"New supplier '{name}'"],
        "records": [],
        "risks": risks,
        "total": None,
        "affected": 1,
        "payload": {"name": name},
    }


def _execute_supplier(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    info = purchasing.create_supplier(name=payload["name"], actor=actor)
    return {
        "summary": f"Supplier {info.name} ({info.code}) created.",
        "links": [{"type": "supplier", "value": info.code, "label": info.name}],
    }


# --- Action 10: stock transfer draft ------------------------------------------------------------

def _build_stock_transfer(actor, *, item: str | None = None, quantity=None,
                          from_warehouse: str | None = None, to_warehouse: str | None = None,
                          **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    resolved = _resolve_item(item or "")
    if resolved is None:
        near = [{"code": i.sku, "name": i.name, "score": round(score, 2)}
                for score, i in _rank(item or "", inventory.list_items(), lambda i: i.name)
                if score >= 0.4][:3]
        return _blocker("item", item, candidates=near)
    source_code, blocked = _resolve_warehouse(from_warehouse)
    if blocked is not None:
        return blocked
    dest_code, blocked = _resolve_warehouse(to_warehouse)
    if blocked is not None:
        return blocked
    if source_code == dest_code:
        return {"error": "Source and destination warehouse must differ."}
    qty = _qty(quantity)
    if qty is None:
        return {"error": "What quantity should be transferred?"}

    risks = []
    on_hand_row = next(
        (r for r in inventory.stock_on_hand(query=resolved.sku, warehouse=source_code)["rows"]
         if r["warehouse_code"] == source_code), None,
    )
    on_hand = Decimal(on_hand_row["quantity"]) if on_hand_row else Decimal("0")
    if qty > on_hand:
        risks.append(f"Only {on_hand} of '{resolved.name}' on hand at {source_code} — "
                     f"transferring {qty} would exceed it.")

    records = [{"type": "item", "value": resolved.sku, "label": resolved.name}]
    return {
        "action": "create_stock_transfer_draft",
        "summary": [
            f"Draft transfer of {qty} {resolved.name} from {source_code} to {dest_code}",
            f"{on_hand} currently on hand at {source_code}",
        ],
        "records": records,
        "risks": risks,
        "total": None,
        "affected": len(records),
        "payload": {"item_sku": resolved.sku, "source_code": source_code,
                    "destination_code": dest_code, "quantity": str(qty)},
    }


def _execute_stock_transfer(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    transfer = inventory.create_stock_transfer_draft(
        item_sku=payload["item_sku"], source_code=payload["source_code"],
        destination_code=payload["destination_code"], quantity=Decimal(payload["quantity"]),
        actor=actor,
    )
    return {
        "summary": f"Draft transfer {transfer.code} created — {transfer.quantity} "
                   f"{transfer.item_name} from {transfer.source_code} to {transfer.destination_code}.",
        "links": [{"type": "stockTransfer", "value": transfer.id, "label": transfer.code}],
    }


# --- Action 11: stock count draft ---------------------------------------------------------------

def _build_stock_count(actor, *, warehouse: str | None = None, scope: str | None = None,
                       **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    warehouse_code, blocked = _resolve_warehouse(warehouse)
    if blocked is not None:
        return blocked
    rows = inventory.stock_on_hand(warehouse=warehouse_code, limit=50)["rows"]
    line_count = len(rows)
    if line_count == 0:
        return {"error": f"No items have a balance at {warehouse_code} to count."}

    records = [{"type": "warehouse", "value": warehouse_code, "label": warehouse_code}]
    return {
        "action": "create_stock_count_draft",
        "summary": [
            f"Start a stock count at {warehouse_code}",
            f"{line_count} item line(s) will be snapshotted",
        ],
        "records": records,
        "risks": [],
        "total": None,
        "affected": line_count,
        "payload": {"warehouse_code": warehouse_code},
    }


def _execute_stock_count(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    count = inventory.create_stock_count_draft(warehouse_code=payload["warehouse_code"], actor=actor)
    return {
        "summary": f"Stock count {count.code} opened at {count.warehouse_code} "
                   f"({count.line_count} line(s)).",
        "links": [{"type": "stockCount", "value": count.id, "label": count.code}],
    }


# --- Action 12: set an item's reorder point -------------------------------------------------------

def _build_set_reorder_point(actor, *, item: str | None = None, reorder_point=None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    resolved = _resolve_item(item or "")
    if resolved is None:
        near = [{"code": i.sku, "name": i.name, "score": round(score, 2)}
                for score, i in _rank(item or "", inventory.list_items(), lambda i: i.name)
                if score >= 0.4][:3]
        return _blocker("item", item, candidates=near)
    new_point = _qty(reorder_point)
    if new_point is None:
        return {"error": "What should the new reorder point be?"}
    on_hand_rows = inventory.stock_on_hand(query=resolved.sku)["rows"]
    on_hand = sum((Decimal(r["quantity"]) for r in on_hand_rows), Decimal("0"))

    records = [{"type": "item", "value": resolved.sku, "label": resolved.name}]
    return {
        "action": "set_reorder_point",
        "summary": [
            f"Set reorder point of {resolved.name} from {resolved.reorder_point} to {new_point}",
            f"{on_hand} currently on hand",
        ],
        "records": records,
        "risks": [],
        "total": None,
        "affected": 1,
        "payload": {"sku": resolved.sku, "reorder_point": str(new_point)},
    }


def _execute_set_reorder_point(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    updated = inventory.set_reorder_point(
        sku=payload["sku"], reorder_point=Decimal(payload["reorder_point"]), actor=actor,
    )
    return {
        "summary": f"Reorder point for {updated.name} set to {updated.reorder_point} "
                   f"(was {updated.previous_reorder_point}).",
        "links": [{"type": "item", "value": updated.sku, "label": updated.name}],
    }


# --- registry -----------------------------------------------------------------------------------

# The harness spec's irreversible list: these kinds can NEVER ship with requires_confirm=False,
# and their confirm card must restate consequences (not just the payload).
DESTRUCTIVE_KINDS = {"delete", "cancel", "approve", "post", "reverse", "close_period",
                     "bulk", "adjust"}


@dataclass(frozen=True)
class Action:
    name: str
    description: str          # for the loop prompt
    args: dict                # arg -> description
    build_proposal: Callable  # (actor, **args) -> {summary, records, risks, payload} | {error}
    execute: Callable         # (actor, payload) -> {links, summary}
    kind: str = "create"      # "create" | "update" | "delete" | "approve" | "post" | "reverse" |
                              # "cancel" | "close_period" | "bulk" | "adjust"
    requires_confirm: bool = True  # NO action may default to False


ACTIONS: dict[str, Action] = {a.name: a for a in [
    Action(
        "create_sales_order_draft",
        "Prepare a DRAFT sales order for a customer (nothing is posted; the user confirms). Use for "
        "'create/make a sales order for <customer> with <n> of <item>'.",
        {"customer": "customer code or name",
         "items": "list of {item (sku or name), quantity}",
         "warehouse": "optional warehouse code to sell from"},
        _build_sales_order, _execute_sales_order,
    ),
    Action(
        "create_purchase_request_draft",
        "Prepare a DRAFT purchase request to a supplier (the user confirms). Set from_low_stock=true "
        "to fill it from items below their reorder point. Use for 'raise a purchase request to "
        "<supplier>' or 'order more of the low-stock items'.",
        {"supplier": "supplier code or name",
         "items": "list of {item (sku or name), quantity, unit_cost (minor units, optional)}",
         "warehouse": "optional warehouse code to receive into",
         "from_low_stock": "true to build the lines from items below reorder point"},
        _build_purchase_request, _execute_purchase_request,
    ),
    Action(
        "create_customer",
        "Create a new customer record by name (the user confirms). Use for 'add a customer called "
        "<name>'. Warns if a similar customer already exists.",
        {"query": "the new customer's name"},
        _build_customer, _execute_customer,
    ),
    Action(
        "create_quotation_draft",
        "Prepare a DRAFT quotation for a customer (nothing is posted; the user confirms). Use for "
        "'quote <customer> for <n> of <item>'.",
        {"customer": "customer code or name",
         "items": "list of {item (sku or name), quantity}",
         "warehouse": "optional warehouse code to quote from"},
        _build_quotation, _execute_quotation,
    ),
    Action(
        "convert_quotation",
        "Turn an already-approved quotation into a DRAFT sales order (the user confirms). Use for "
        "'turn quotation <number> into an order' or 'convert <customer>'s quote'. Refuses to "
        "execute a quotation that isn't approved yet.",
        {"query": "quotation number or customer name to find the quotation"},
        _build_convert_quotation, _execute_convert_quotation,
    ),
    Action(
        "edit_sales_order_draft",
        "Change the lines on a sales order that is still a DRAFT (the user confirms). Use for "
        "'change the draft order <number> to <n> of <item>'. Refused with no card if the order is "
        "no longer a draft.",
        {"query": "the order number",
         "items": "new/changed lines: list of {item (sku or name), quantity, "
                  "unit_price (minor units, optional — priced automatically if omitted)}"},
        _build_edit_sales_order, _execute_edit_sales_order,
    ),
    Action(
        "create_purchase_order_draft",
        "Prepare a DRAFT purchase order directly to a supplier (nothing is posted; the user "
        "confirms). Use for 'raise/draft a PO to <supplier> for <n> of <item>'.",
        {"supplier": "supplier code or name",
         "items": "list of {item (sku or name), quantity, unit_cost (minor units, optional)}",
         "warehouse": "optional warehouse code to receive into"},
        _build_purchase_order, _execute_purchase_order,
    ),
    Action(
        "convert_purchase_request",
        "Turn an already-approved purchase request into a DRAFT purchase order (the user "
        "confirms). Use for 'turn request <number> into an order' or 'convert <supplier>'s "
        "request'. Refuses to execute a request that isn't approved yet.",
        {"query": "request number or supplier name to find the purchase request"},
        _build_convert_purchase_request, _execute_convert_purchase_request,
    ),
    Action(
        "create_supplier",
        "Create a new supplier record by name (the user confirms). Use for 'add a supplier called "
        "<name>'. Warns if a similar supplier already exists.",
        {"query": "the new supplier's name"},
        _build_supplier, _execute_supplier,
    ),
    Action(
        "create_stock_transfer_draft",
        "Prepare a DRAFT stock transfer of one item between two warehouses (nothing moves until "
        "the user confirms). Use for 'move/transfer <n> of <item> from <warehouse A> to "
        "<warehouse B>'. Flags a risk if the quantity exceeds on-hand at the source.",
        {"item": "item sku or name to transfer",
         "quantity": "quantity to transfer",
         "from_warehouse": "source warehouse code",
         "to_warehouse": "destination warehouse code"},
        _build_stock_transfer, _execute_stock_transfer,
    ),
    Action(
        "create_stock_count_draft",
        "Open a DRAFT stock count for a warehouse, snapshotting current system quantities (the user "
        "confirms; counted figures are entered and posted later on the count screen). Use for "
        "'start/open a stock count in <warehouse>'.",
        {"warehouse": "warehouse code to count",
         "scope": "optional category or 'all' — currently counts every item with a balance there"},
        _build_stock_count, _execute_stock_count,
    ),
    Action(
        "set_reorder_point",
        "Update an item's reorder point (master-data edit, no stock movement; the user confirms). "
        "Use for 'set the reorder point of <item> to <n>'.",
        {"item": "item sku or name",
         "reorder_point": "the new reorder point quantity"},
        _build_set_reorder_point, _execute_set_reorder_point,
        kind="update",
    ),
]}

for _a in ACTIONS.values():
    assert _a.requires_confirm or _a.kind not in DESTRUCTIVE_KINDS, (
        f"action {_a.name}: destructive kind '{_a.kind}' must require confirmation")

# Which loop-decision fields can feed an action argument (each action gets only the args it declares).
ACTION_ARG_FIELDS = ("customer", "items", "supplier", "warehouse", "from_low_stock", "query",
                    "item", "quantity", "from_warehouse", "to_warehouse", "reorder_point", "scope")


def catalog_text() -> str:
    """Compact description of the proposable actions for the planner prompt."""
    lines = ["Write actions you may PROPOSE (never execute — the user confirms a card):"]
    for a in ACTIONS.values():
        args = ", ".join(f"{k} ({v})" for k, v in a.args.items()) or "no arguments"
        lines.append(f"- {a.name}: {a.description} Arguments: {args}")
    return "\n".join(lines)


def build(actor, name: str, decision: dict) -> dict:
    """Build one proposal from a planner decision. Returns the proposal dict, or ``{error}`` on a
    refusal / unresolved input (fed back so the loop answers calmly, no card)."""
    action = ACTIONS.get(name)
    if action is None:
        return {"error": f"There is no action named '{name}'."}
    kwargs = {k: decision[k] for k in ACTION_ARG_FIELDS
              if decision.get(k) is not None and k in action.args}
    try:
        proposal = action.build_proposal(actor, **kwargs)
    except Exception:  # bad argument shape — a calm note, never a crash
        return {"error": "That could not be prepared. Try rephrasing what to create."}
    if "error" not in proposal and "blocker" not in proposal:
        proposal["kind"] = action.kind
    return proposal


def execute(actor, name: str, payload: dict) -> dict:
    """Run a confirmed action's write as the actor. Raises on a refused/invalid confirm (the view
    turns that into the right status code)."""
    action = ACTIONS.get(name)
    if action is None:
        raise ValueError(f"unknown action {name}")
    return action.execute(actor, payload)
