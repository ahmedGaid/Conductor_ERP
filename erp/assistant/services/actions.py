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

import datetime as _dt
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from difflib import SequenceMatcher

from erp.accounting import contracts as accounting
from erp.crm import contracts as crm
from erp.identity.roles import ACCOUNTANT, BRANCH_MANAGER, SYSTEM_ADMIN
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


def _posting_enabled() -> bool:
    from erp.identity.services import get_org_preferences
    return get_org_preferences().assistant_posting_enabled


def _refused_posting_disabled() -> dict:
    return {"error": "Posting actions aren't turned on for this workspace. Ask your System Admin "
                     "to enable them in Settings → Organization."}


def _can_post(actor, *roles: str) -> bool:
    """Gate for any risk="post" action: the org toggle AND the same role check a draft action
    would use. Neither check replaces the other."""
    return _posting_enabled() and _can(actor, *roles)


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


def _minor(value) -> int:
    """A journal-line amount → non-negative integer minor units (0 when absent/garbage)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


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


def _resolve_account(query: str) -> accounting.AccountInfo | None:
    """An account query → one AccountInfo: exact code wins, else the best name match (>=0.6)."""
    q = (query or "").strip()
    if not q:
        return None
    exact = accounting.find_account(q)
    if exact is not None:
        return exact
    ranked = _rank(q, accounting.list_accounts(), lambda a: a.name)
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


# --- Action (posting): approve a purchase request --------------------------------------------------
# One status step earlier than convert_purchase_request in the same request lifecycle. Nothing posts
# to the GL or stock here — approving only unlocks the request for conversion later — but it's still
# consequential (authorizes spend), so it's gated and confirmed like the other posting actions.

def _build_approve_purchase_request(actor, *, query: str | None = None, **_) -> dict:
    if not _posting_enabled():
        return _refused_posting_disabled()
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    q = (query or "").strip()
    if not q:
        return {"error": "Which request? Give its number or the supplier's name."}
    matches = purchasing.find_requests(actor, query=q, limit=5)
    if not matches:
        return _blocker("purchase request", q)
    exact = [m for m in matches if m["number"].lower() == q.lower()]
    if len(matches) > 1 and not exact:
        candidates = [{"code": m["number"], "name": m["supplier_name"]} for m in matches[:3]]
        return _blocker("purchase request", q, candidates=candidates)
    req = exact[0] if exact else matches[0]

    if req["status"] != "submitted":
        return {"error": f"Request {req['number']} is '{req['status']}' — only a submitted "
                         "request awaiting approval can be approved."}

    return {
        "action": "approve_purchase_request",
        "summary": [
            f"Approve {req['number']} ({req['supplier_name']})",
            f"{len(req['lines'])} line(s), total {_egp(req['subtotal_minor'])}",
        ],
        "records": [{"type": "purchaseRequest", "value": req["id"], "label": req["number"]}],
        "risks": [],
        "total": _egp(req["subtotal_minor"]),
        "affected": 1,
        "challenge": challenge(req["subtotal_minor"]),
        "payload": {"request_id": req["id"]},
    }


def _execute_approve_purchase_request(actor, payload: dict) -> dict:
    if not _can_post(actor, BRANCH_MANAGER):
        raise PermissionError
    req = purchasing.get_request(actor, payload["request_id"])
    if req is None:
        raise ValueError("purchase request not found")
    purchasing.approve_request(req, actor=actor)
    return {
        "summary": f"Approved {req.number}.",
        "links": [{"type": "purchaseRequest", "value": str(req.id), "label": req.number}],
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


# --- Action (posting): issue stock entry ------------------------------------------------------
# Consumption out of stock — posts COGS. The GL value is only known once issue_stock actually runs
# (it locks the balance row); this proposal can only ESTIMATE it from the current weighted-average
# unit cost. The confirmed result card shows the actual posted value, which is authoritative.

def _build_issue_stock_entry(actor, *, item: str | None = None, quantity=None,
                             warehouse: str | None = None, **_) -> dict:
    if not _posting_enabled():
        return _refused_posting_disabled()
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    resolved = _resolve_item(item or "")
    if resolved is None:
        near = [{"code": i.sku, "name": i.name, "score": round(score, 2)}
                for score, i in _rank(item or "", inventory.list_items(), lambda i: i.name)
                if score >= 0.4][:3]
        return _blocker("item", item, candidates=near)
    warehouse_code, blocked = _resolve_warehouse(warehouse)
    if blocked is not None:
        return blocked
    qty = _qty(quantity)
    if qty is None:
        return {"error": "What quantity should be issued?"}

    on_hand_row = next(
        (r for r in inventory.stock_on_hand(query=resolved.sku, warehouse=warehouse_code)["rows"]
         if r["warehouse_code"] == warehouse_code), None,
    )
    on_hand = Decimal(on_hand_row["quantity"]) if on_hand_row else Decimal("0")
    if qty > on_hand:
        return {"error": f"Only {on_hand} of '{resolved.name}' on hand at {warehouse_code} — "
                         f"can't issue {qty}."}
    est_value_minor = (round(Decimal(on_hand_row["value_minor"]) * qty / on_hand)
                       if on_hand > 0 else 0)

    records = [{"type": "item", "value": resolved.sku, "label": resolved.name}]
    return {
        "action": "issue_stock_entry",
        "summary": [
            f"Issue {qty} {resolved.name} from {warehouse_code}",
            f"Estimated value {_egp(est_value_minor)} (posts to COGS)",
        ],
        "records": records,
        "risks": [],
        "total": _egp(est_value_minor),
        "affected": 1,
        "challenge": challenge(est_value_minor),
        "payload": {"item_sku": resolved.sku, "warehouse_code": warehouse_code, "quantity": str(qty)},
    }


def _execute_issue_stock_entry(actor, payload: dict) -> dict:
    if not _can_post(actor, BRANCH_MANAGER):
        raise PermissionError
    movement = inventory.issue(
        payload["item_sku"], payload["warehouse_code"], Decimal(payload["quantity"]), actor=actor,
    )
    return {
        "summary": f"Issued {movement.quantity} {movement.item.name} from {movement.warehouse.code} "
                   f"— {_egp(movement.value_minor)} posted to COGS.",
        "links": [{"type": "item", "value": movement.item.sku, "label": movement.item.name}],
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


# --- Action 13: journal entry draft ---------------------------------------------------------------

def _build_journal_entry(actor, *, lines=None, date: str | None = None,
                         reference: str | None = None, **_) -> dict:
    if not _can(actor, ACCOUNTANT, BRANCH_MANAGER):
        return _refused()
    entries = list(lines or [])
    if len(entries) < 2:
        return {"error": "A journal entry needs at least two lines."}

    resolved_lines, records, risks = [], [], []
    seen_codes: set[str] = set()
    total_debit = total_credit = 0
    for entry in entries:
        query = (entry.get("account") if isinstance(entry, dict) else None) or ""
        account = _resolve_account(query)
        if account is None:
            return {"error": f"Account '{query}' was not found. Give its code or exact name."}
        if not account.is_active or not account.is_postable:
            reason = "inactive" if not account.is_active else "a group account and cannot be posted to"
            return {"error": f"'{account.name}' is {reason}."}
        debit = _minor(entry.get("debit")) if isinstance(entry, dict) else 0
        credit = _minor(entry.get("credit")) if isinstance(entry, dict) else 0
        if (debit > 0) == (credit > 0):
            return {"error": f"'{account.name}' line needs exactly one of debit or credit, "
                             "not both or neither."}
        memo = ((entry.get("memo") if isinstance(entry, dict) else "") or "").strip()
        total_debit += debit
        total_credit += credit
        resolved_lines.append({"account_code": account.code, "debit": debit, "credit": credit,
                               "memo": memo})
        if account.code not in seen_codes:
            records.append({"type": "account", "value": account.code, "label": account.name})
            seen_codes.add(account.code)

    if total_debit != total_credit:
        gap = abs(total_debit - total_credit)
        return {"error": f"Debits and credits do not match — {_egp(total_debit)} debit vs "
                         f"{_egp(total_credit)} credit, a gap of {_egp(gap)}."}

    entry_date = (date or "").strip() or _dt.date.today().isoformat()
    return {
        "action": "create_journal_entry_draft",
        "summary": [
            f"Draft journal entry, {len(resolved_lines)} line(s)",
            f"debit {_egp(total_debit)} = credit {_egp(total_credit)}",
        ],
        "records": records,
        "risks": risks,
        "total": _egp(total_debit),
        "affected": len(records),
        "payload": {"lines": resolved_lines, "date": entry_date,
                    "reference": (reference or "").strip()},
    }


def _execute_journal_entry(actor, payload: dict) -> dict:
    if not _can(actor, ACCOUNTANT, BRANCH_MANAGER):
        raise PermissionError
    entry = accounting.create_journal_entry_draft(
        accounting.JournalInput(
            date=_dt.date.fromisoformat(payload["date"]),
            lines=[accounting.LineInput(account_code=ln["account_code"], debit=ln["debit"],
                                        credit=ln["credit"], memo=ln.get("memo", ""))
                   for ln in payload["lines"]],
            reference=payload.get("reference", ""), source="assistant",
        ),
        actor=actor,
    )
    return {
        "summary": f"Draft journal entry {entry.number} created (unposted).",
        "links": [{"type": "journalEntry", "value": str(entry.id), "label": entry.number}],
    }


# --- Action (posting): post a drafted journal entry -----------------------------------------------
# The first risk="post" action. Two gates, both mirroring FILE_01: the org toggle (a workspace that
# hasn't turned posting on gets a calm refusal that names Settings) AND the same role a draft would
# need. The proposal carries a typed retype ``challenge`` the card makes the user match before the
# confirm endpoint will spend it.

def _build_post_journal_entry(actor, *, query=None, **_) -> dict:
    if not _posting_enabled():
        return _refused_posting_disabled()
    if not _can(actor, ACCOUNTANT, BRANCH_MANAGER):
        return _refused()
    drafts = [j for j in accounting.find_journal(actor, query=(query or "").strip())
              if j["status"] == "draft"]
    if not drafts:
        return {"error": f"No draft journal entry matches '{query}'. Give its number, "
                         "or draft one first."}
    if len(drafts) > 1:
        return {"error": "More than one draft journal entry matches that — use the entry number."}
    entry = accounting.get_journal_entry(actor, drafts[0]["id"])
    if entry is None or entry.status != "draft":  # edited/posted between the list and now
        return {"error": "That draft journal entry is no longer available to post."}

    lines = list(entry.lines.all())
    total = sum(line.debit for line in lines)
    return {
        "action": "post_journal_entry_draft",
        "summary": [
            f"Post journal entry {entry.number}, {len(lines)} line(s)",
            f"debit {_egp(total)} = credit {_egp(total)}",
        ],
        "records": [{"type": "journalEntry", "value": str(entry.id), "label": entry.number}],
        "risks": [f"Posts {entry.number} to the general ledger — permanent once posted "
                  "(reverse it, never edit)."],
        "total": _egp(total),
        "affected": 1,
        "challenge": challenge(total, entry.currency),
        "payload": {"entry_id": str(entry.id)},
    }


def _execute_post_journal_entry(actor, payload: dict) -> dict:
    if not _can_post(actor, ACCOUNTANT, BRANCH_MANAGER):
        raise PermissionError
    entry = accounting.get_journal_entry(actor, payload["entry_id"])
    if entry is None:
        raise ValueError("journal entry not found")
    total = sum(line.debit for line in entry.lines.all())
    accounting.enforce_journal_approval(actor, total)
    posted = accounting.post_draft_journal_entry(entry, actor=actor)
    return {
        "summary": f"Journal entry {posted.number} posted to the general ledger.",
        "links": [{"type": "journalEntry", "value": str(posted.id), "label": posted.number}],
    }


# --- Action (posting): receive a purchase order ----------------------------------------------------
# v1 = full receipt only, on every unreceived line — no natural-language partial-quantity parsing
# (matches the descoping precedent other posting actions in this file use to keep scope tight).

def _build_receive_purchase_order(actor, *, query: str | None = None, **_) -> dict:
    if not _posting_enabled():
        return _refused_posting_disabled()
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    q = (query or "").strip()
    if not q:
        return {"error": "Which purchase order? Give its number or the supplier's name."}
    matches = purchasing.find_orders(actor, query=q, limit=5)
    if not matches:
        return _blocker("purchase order", q)
    exact = [m for m in matches if m["number"].lower() == q.lower()]
    if len(matches) > 1 and not exact:
        candidates = [{"code": m["number"], "name": m["supplier_name"]} for m in matches[:3]]
        return _blocker("purchase order", q, candidates=candidates)
    order = exact[0] if exact else matches[0]

    if order["status"] not in ("confirmed", "partially_received"):
        return {"error": f"Order {order['number']} is '{order['status']}' — it needs to be "
                         "confirmed before it can be received."}

    remaining = [(ln, Decimal(ln["quantity"]) - Decimal(ln["received_qty"])) for ln in order["lines"]]
    remaining = [(ln, qty) for ln, qty in remaining if qty > 0]
    total = sum(
        int((qty * Decimal(ln["unit_cost_minor"])).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        for ln, qty in remaining
    )
    return {
        "action": "receive_purchase_order",
        "summary": [
            f"Receive {order['number']} ({order['supplier_name']}) in full — {len(remaining)} line(s)",
            *[f"{ln['item_sku']}: {qty} remaining" for ln, qty in remaining],
        ],
        "records": [{"type": "purchaseOrder", "value": order["id"], "label": order["number"]}],
        "risks": [],
        "total": _egp(total),
        "affected": 1,
        "challenge": challenge(total),
        "payload": {"order_id": order["id"]},
    }


def _execute_receive_purchase_order(actor, payload: dict) -> dict:
    if not _can_post(actor, BRANCH_MANAGER):
        raise PermissionError
    order = purchasing.get_order(actor, payload["order_id"])
    if order is None:
        raise ValueError("purchase order not found")
    purchasing.receive_order(order, actor=actor)
    return {
        "summary": f"Received {order.number} in full.",
        "links": [{"type": "purchaseOrder", "value": str(order.id), "label": order.number}],
    }


# --- Action (posting): bill a purchase order ---------------------------------------------------
# 3-way match: bill_order refuses if any line's received_qty != quantity — surfaced here too,
# before confirm, so the user never sees a card that would fail (mirrors edit_sales_order_draft's
# proposal-time precondition check).

def _build_bill_purchase_order(actor, *, query: str | None = None, **_) -> dict:
    if not _posting_enabled():
        return _refused_posting_disabled()
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    q = (query or "").strip()
    if not q:
        return {"error": "Which purchase order? Give its number or the supplier's name."}
    matches = purchasing.find_orders(actor, query=q, limit=5)
    if not matches:
        return _blocker("purchase order", q)
    exact = [m for m in matches if m["number"].lower() == q.lower()]
    if len(matches) > 1 and not exact:
        candidates = [{"code": m["number"], "name": m["supplier_name"]} for m in matches[:3]]
        return _blocker("purchase order", q, candidates=candidates)
    order = purchasing.get_order(actor, (exact[0] if exact else matches[0])["id"])
    if order is None:
        return {"error": "That purchase order is no longer available."}

    if order.status not in ("received", "partially_received"):
        return {"error": f"Order {order.number} is '{order.status}' — it needs to be received "
                         "before it can be billed."}
    for ln in order.lines.all():
        if Decimal(ln.received_qty) != Decimal(ln.quantity):
            return {"error": f"Order {order.number} is only partially received (line "
                             f"{ln.line_no}: {ln.received_qty} of {ln.quantity}) — it can't be "
                             "billed until every line is fully received."}

    net = order.received_minor
    vat = accounting.compute_tax(net, order.tax_code) if order.tax_code else 0
    gross = net + vat
    return {
        "action": "bill_purchase_order",
        "summary": [
            f"Bill {order.number} ({order.supplier.name})",
            f"net {_egp(net)} + VAT {_egp(vat)} = {_egp(gross)}",
        ],
        "records": [{"type": "purchaseOrder", "value": str(order.id), "label": order.number}],
        "risks": [],
        "total": _egp(gross),
        "affected": 1,
        "challenge": challenge(gross),
        "payload": {"order_id": str(order.id)},
    }


def _execute_bill_purchase_order(actor, payload: dict) -> dict:
    if not _can_post(actor, BRANCH_MANAGER):
        raise PermissionError
    order = purchasing.get_order(actor, payload["order_id"])
    if order is None:
        raise ValueError("purchase order not found")
    purchasing.bill_order(order, actor=actor)
    return {
        "summary": f"Billed {order.number} — bill {order.bill_number}.",
        "links": [{"type": "purchaseOrder", "value": str(order.id), "label": order.number}],
    }


# --- Action (posting): pay a purchase order ------------------------------------------------------
# amount is optional — defaults to the full outstanding balance, mirrors PaymentDialog.tsx's manual
# behaviour (defaults to outstanding, human can edit down for a partial payment).

def _build_pay_purchase_order(actor, *, query: str | None = None, amount=None, **_) -> dict:
    if not _posting_enabled():
        return _refused_posting_disabled()
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    q = (query or "").strip()
    if not q:
        return {"error": "Which purchase order? Give its number or the supplier's name."}
    matches = purchasing.find_orders(actor, query=q, limit=5)
    if not matches:
        return _blocker("purchase order", q)
    exact = [m for m in matches if m["number"].lower() == q.lower()]
    if len(matches) > 1 and not exact:
        candidates = [{"code": m["number"], "name": m["supplier_name"]} for m in matches[:3]]
        return _blocker("purchase order", q, candidates=candidates)
    order = exact[0] if exact else matches[0]

    if order["status"] != "billed":
        return {"error": f"Order {order['number']} is '{order['status']}' — it needs to be "
                         "billed first before it can be paid."}
    amount_minor = _minor(amount) if amount else order["outstanding_minor"]
    if amount_minor <= 0 or amount_minor > order["outstanding_minor"]:
        return {"error": f"That amount doesn't work — {_egp(order['outstanding_minor'])} is "
                         f"outstanding on {order['number']}."}

    return {
        "action": "pay_purchase_order",
        "summary": [
            f"Pay {order['number']} ({order['supplier_name']})",
            f"{_egp(amount_minor)} of {_egp(order['outstanding_minor'])} outstanding",
        ],
        "records": [{"type": "purchaseOrder", "value": order["id"], "label": order["number"]}],
        "risks": [],
        "total": _egp(amount_minor),
        "affected": 1,
        "challenge": challenge(amount_minor),
        "payload": {"order_id": order["id"], "amount_minor": amount_minor},
    }


def _execute_pay_purchase_order(actor, payload: dict) -> dict:
    if not _can_post(actor, BRANCH_MANAGER):
        raise PermissionError
    order = purchasing.get_order(actor, payload["order_id"])
    if order is None:
        raise ValueError("purchase order not found")
    purchasing.pay_order(order, payload["amount_minor"], actor=actor)
    return {
        "summary": f"Paid {_egp(payload['amount_minor'])} on {order.number} — now {order.status}.",
        "links": [{"type": "purchaseOrder", "value": str(order.id), "label": order.number}],
    }


# --- Action 14: create account --------------------------------------------------------------------

_ACCOUNT_TYPES = {"asset", "liability", "equity", "income", "expense"}


def _build_create_account(actor, *, name: str | None = None, type: str | None = None,
                          code: str | None = None, parent: str | None = None, **_) -> dict:
    if not _can(actor, ACCOUNTANT, BRANCH_MANAGER):
        return _refused()
    account_name = (name or "").strip()
    if not account_name:
        return {"error": "What name should the new account have?"}
    account_type = (type or "").strip().lower()
    if account_type not in _ACCOUNT_TYPES:
        return {"error": "Account type must be asset, liability, equity, income or expense."}

    everyone = accounting.list_accounts()
    parent_account = None
    if (parent or "").strip():
        parent_account = _resolve_account(parent)
        if parent_account is None:
            return {"error": f"Parent account '{parent}' was not found."}

    requested_code = (code or "").strip()
    if requested_code and any(a.code == requested_code for a in everyone):
        return {"error": f"Account code '{requested_code}' is already in use."}
    preview_code = requested_code or accounting.next_account_code(account_type)

    risks = []
    target = account_name.casefold()
    dupes = [a for a in everyone if a.name.casefold().strip() == target]
    if dupes:
        joined = ", ".join(f"{a.name} ({a.code})" for a in dupes)
        risks.append(f"An account named '{account_name}' already exists: {joined}.")
    else:
        near = [a for score, a in _rank(account_name, everyone, lambda a: a.name)
                if score >= 0.7][:3]
        if near:
            joined = ", ".join(f"{a.name} ({a.code})" for a in near)
            risks.append(f"Similar accounts already exist: {joined}.")

    records = []
    if parent_account is not None:
        records.append({"type": "account", "value": parent_account.code,
                        "label": parent_account.name})
    return {
        "action": "create_account",
        "summary": [
            f"New {account_type} account '{account_name}' ({preview_code})",
            f"Under {parent_account.name}" if parent_account is not None else "Top level",
        ],
        "records": records,
        "risks": risks,
        "total": None,
        "affected": 1,
        "payload": {"name": account_name, "type": account_type, "code": requested_code,
                    "parent_code": parent_account.code if parent_account is not None else ""},
    }


def _execute_create_account(actor, payload: dict) -> dict:
    if not _can(actor, ACCOUNTANT, BRANCH_MANAGER):
        raise PermissionError
    account = accounting.create_account(
        name=payload["name"], type=payload["type"], code=payload.get("code", ""),
        parent_code=payload.get("parent_code", ""), actor=actor,
    )
    if account is None:
        raise ValueError("parent account no longer exists")
    return {
        "summary": f"Account {account.name} ({account.code}) created.",
        "links": [{"type": "account", "value": account.code, "label": account.name}],
    }


# --- Action 15: create opportunity -----------------------------------------------------------------

def _build_create_opportunity(actor, *, customer: str | None = None, name: str | None = None,
                              value: int | None = None, expected_close: str | None = None,
                              **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    deal_name = (name or "").strip()
    if not deal_name:
        return {"error": "What should the deal be called?"}
    cust = (customer or "").strip()
    if not cust:
        return {"error": "Which customer is this opportunity for?"}

    customers = sales.find_customers(actor, query=cust, limit=3)
    if not customers:
        return _blocker("customer", cust)
    if len(customers) > 1:
        near = [{"code": c["code"], "name": c["name"], "score": round(score, 2)}
                for score, c in _rank(cust, customers, lambda c: c["name"]) if score >= 0.4][:3]
        if near:
            return _blocker("customer", cust, candidates=near)
    customer_code = customers[0]["code"]
    customer_name = customers[0]["name"]

    amount_minor = value or 0
    close_date = (expected_close or "").strip() or None

    records = [{"type": "customer", "value": customer_code, "label": customer_name}]
    summary = [f"New opportunity '{deal_name}' for {customer_code}"]
    if amount_minor > 0:
        summary.append(f"worth {_egp(amount_minor)}")
    if close_date:
        summary.append(f"close by {close_date}")
    return {
        "action": "create_opportunity",
        "summary": summary,
        "records": records,
        "risks": [],
        "total": _egp(amount_minor) if amount_minor > 0 else None,
        "affected": 1,
        "payload": {"customer_code": customer_code, "name": deal_name, "amount_minor": amount_minor,
                    "expected_close": close_date},
    }


def _execute_create_opportunity(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    opp = crm.create_opportunity(
        name=payload["name"], customer_code=payload["customer_code"],
        expected_close=payload.get("expected_close"), actor=actor,
    )
    return {
        "summary": f"Opportunity {opp.number} created for {payload['customer_code']}.",
        "links": [{"type": "opportunity", "value": str(opp.id), "label": opp.number}],
    }


# --- Action 16: advance opportunity stage ----------------------------------------------------------

def _build_advance_opportunity_stage(actor, *, query: str | None = None,
                                     stage: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    q = (query or "").strip()
    if not q:
        return {"error": "Which opportunity? Give its number or name."}
    matches = crm.find_opportunities(actor, query=q, limit=5)
    if not matches:
        return _blocker("opportunity", q)
    opp = matches[0]

    if opp["stage"] not in ("qualifying", "proposal", "negotiation"):
        return {"error": f"Cannot advance a {opp['stage']} opportunity."}

    target_stage = (stage or "").strip().lower()
    valid_stages = ["qualifying", "proposal", "negotiation"]
    if target_stage not in valid_stages:
        return {"error": f"Target stage must be one of: {', '.join(valid_stages)}."}
    if opp["stage"] == target_stage:
        return {"error": f"Opportunity is already in stage '{opp['stage']}'."}

    risks = []
    stage_order = {"qualifying": 0, "proposal": 1, "negotiation": 2}
    if stage_order.get(target_stage, 0) < stage_order.get(opp["stage"], 0):
        risks.append(f"Moving backward from '{opp['stage']}' to '{target_stage}'.")

    records = [
        {"type": "customer", "value": opp["customer_code"], "label": opp["customer_code"]},
        {"type": "opportunity", "value": opp["number"], "label": opp["number"]},
    ]
    return {
        "action": "advance_opportunity_stage",
        "summary": [
            f"Move {opp['number']} from {opp['stage']} to {target_stage}",
            f"Customer: {opp['customer_code']}",
        ],
        "records": records,
        "risks": risks,
        "total": None,
        "affected": 1,
        "payload": {"opportunity_number": opp["number"], "stage": target_stage},
    }


def _execute_advance_opportunity_stage(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    from erp.crm.domain.models import Opportunity
    opp = Opportunity.objects.get(number=payload["opportunity_number"])
    opp = crm.advance_stage(opp, stage=payload["stage"], actor=actor)
    return {
        "summary": f"Opportunity {opp.number} moved to {opp.stage}.",
        "links": [{"type": "opportunity", "value": str(opp.id), "label": opp.number}],
    }


# --- Action 17: log activity -----------------------------------------------------------------------

def _build_log_activity(actor, *, query: str | None = None, note: str | None = None,
                        type: str | None = None, **_) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    record_query = (query or "").strip()
    if not record_query:
        return {"error": "Which customer or opportunity is this activity for?"}
    activity_note = (note or "").strip()
    if not activity_note:
        return {"error": "What is the activity note?"}

    activity_type = (type or "note").strip().lower()
    valid_types = ["call", "email", "meeting", "task", "note"]
    if activity_type not in valid_types:
        activity_type = "note"

    opps = crm.find_opportunities(actor, query=record_query, limit=5)
    customers = sales.find_customers(actor, query=record_query, limit=5)

    candidates = []
    if opps:
        for o in opps:
            candidates.append({"type": "opportunity", "number": o["number"], "customer": o["customer_code"]})
    if customers:
        for c in customers:
            candidates.append({"type": "customer", "code": c["code"], "name": c["name"]})

    if not candidates:
        return _blocker("customer or opportunity", record_query)
    if len(candidates) > 1:
        return _blocker("customer or opportunity", record_query,
                       candidates=[c.get("number") or c.get("code") for c in candidates[:3]])

    target = candidates[0]
    if target["type"] == "opportunity":
        related_type = "opportunity"
        related_ref = target["number"]
        label = f"{target['number']}"
    else:
        related_type = "customer"
        related_ref = target["code"]
        label = f"{target['name']} ({target['code']})"

    records = [{"type": target["type"], "value": related_ref, "label": label}]
    return {
        "action": "log_activity",
        "summary": [f"Log {activity_type}: {activity_note[:40]}..."],
        "records": records,
        "risks": [],
        "total": None,
        "affected": 1,
        "payload": {"related_type": related_type, "related_ref": related_ref,
                    "subject": activity_note, "type": activity_type},
    }


def _execute_log_activity(actor, payload: dict) -> dict:
    if not _can(actor, BRANCH_MANAGER):
        raise PermissionError
    activity = crm.log_activity(
        type=payload["type"], subject=payload["subject"],
        related_type=payload["related_type"], related_ref=payload["related_ref"],
        actor=actor,
    )
    return {
        "summary": f"Activity logged: {payload['subject'][:40]}...",
        "links": [{"type": payload["related_type"], "value": payload["related_ref"],
                   "label": payload["related_ref"]}],
    }


# --- registry -----------------------------------------------------------------------------------

# The harness spec's irreversible list: these kinds can NEVER ship with requires_confirm=False,
# and their confirm card must restate consequences (not just the payload).
DESTRUCTIVE_KINDS = {"delete", "cancel", "approve", "post", "reverse", "close_period",
                     "bulk", "adjust"}


@dataclass(frozen=True)
class Effect:
    """One declared consequence of an action — what entity it touches and how hard."""
    entity: str          # "sales_order", "journal_entry", "customer", ...
    verb: str            # "create" | "update"
    gl: str = "none"     # GL impact class: "none" | "draft" | "posts"
    stock: str = "none"  # stock impact class: "none" | "draft" | "moves"


RISK_LEVELS = ("read", "draft", "post", "destructive")


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
    # --- L0 declared semantics (safe defaults keep undeclared actions working unchanged) ---------
    requires: tuple[str, ...] = ()     # entity kinds that must exist first, e.g. ("customer", "item")
    effects: tuple[Effect, ...] = ()   # what it creates/updates
    invariants: tuple[str, ...] = ()   # verifier pack names to run after execute (FILE_02)
    compensation: str | None = None    # action name that undoes this one; None = draft-delete suffices
    risk: str = "draft"                # "read" | "draft" | "post" | "destructive"
    idempotency: tuple[str, ...] = ()  # payload keys whose values form the natural retry key


ACTIONS: dict[str, Action] = {a.name: a for a in [
    Action(
        "create_sales_order_draft",
        "Prepare a DRAFT sales order for a customer (nothing is posted; the user confirms). Use for "
        "'create/make a sales order for <customer> with <n> of <item>'.",
        {"customer": "customer code or name",
         "items": "list of {item (sku or name), quantity}",
         "warehouse": "optional warehouse code to sell from"},
        _build_sales_order, _execute_sales_order,
        requires=("customer", "item", "warehouse"),
        effects=(Effect("sales_order", "create", stock="draft"),),
        invariants=("doc_totals", "period_open"),
        risk="draft",
        # Names match the EXECUTE payload (``_build_sales_order``'s "payload" key), not the build
        # decision's arg names — ``idempotency_key`` hashes the payload the confirm actually runs.
        idempotency=("customer_code", "lines"),
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
        effects=(Effect("customer", "create"),),
        risk="draft",
        idempotency=("name",),  # execute payload key (build decision's arg is "query")
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
        requires=("item", "warehouse"),
        effects=(Effect("stock_transfer", "create", stock="draft"),),
        invariants=("stock_non_negative",),
        risk="draft",
        # Execute payload keys (build decision's args are item/from_warehouse/to_warehouse).
        idempotency=("item_sku", "quantity", "source_code", "destination_code"),
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
    Action(
        "create_journal_entry_draft",
        "Prepare a DRAFT (unposted) journal entry (the user confirms; posting happens later on "
        "the journal screen). Use for 'draft a journal: debit <account> <amount>, credit "
        "<account> <amount>'. Refuses with no card if debits and credits do not balance.",
        {"lines": "list of {account (code or name), debit (minor units, optional), "
                  "credit (minor units, optional), memo (optional)} — two or more lines, "
                  "debits must equal credits",
         "date": "optional entry date (defaults to today)",
         "reference": "optional reference text"},
        _build_journal_entry, _execute_journal_entry,
        requires=("account",),
        effects=(Effect("journal_entry", "create", gl="draft"),),
        invariants=("journal_balanced", "period_open"),
        risk="draft",
        idempotency=("lines", "date"),
    ),
    Action(
        "post_journal_entry_draft",
        "Post an existing DRAFT journal entry to the general ledger (the user confirms by retyping "
        "the amount; posting is permanent — reverse, never edit). Use for 'post journal entry "
        "<number>'. Refused with no card if no draft matches, or if posting actions are turned off "
        "for this workspace.",
        {"query": "journal entry number, reference or memo to find the draft to post"},
        _build_post_journal_entry, _execute_post_journal_entry,
        kind="post",
        effects=(Effect("journal_entry", "update", gl="posts"),),
        invariants=("journal_balanced", "period_open"),
        risk="post",
        idempotency=("entry_id",),
    ),
    Action(
        "receive_purchase_order",
        "Receive a confirmed purchase order in full — goods receipt (GRN), raises stock on hand "
        "and clears GRNI per the normal 3-way match (the user confirms by retyping the amount; "
        "posting is permanent). Use for 'receive PO <number>' or 'receive the order from "
        "<supplier>'. Refused with no card if the order isn't confirmed yet, or if posting actions "
        "are turned off for this workspace.",
        {"query": "purchase order number or supplier name to find the order to receive"},
        _build_receive_purchase_order, _execute_receive_purchase_order,
        kind="post",
        effects=(Effect("purchase_order", "update", stock="moves"),),
        invariants=("stock_non_negative",),
        risk="post",
        idempotency=("order_id",),
    ),
    Action(
        "bill_purchase_order",
        "Bill a received purchase order — 3-way match, clears GRNI into AP and books VAT input "
        "(the user confirms by retyping the amount; posting is permanent). Use for 'bill PO "
        "<number>' or 'bill the order from <supplier>'. Refused with no card if the order isn't "
        "fully received yet, or if posting actions are turned off for this workspace.",
        {"query": "purchase order number or supplier name to find the order to bill"},
        _build_bill_purchase_order, _execute_bill_purchase_order,
        kind="post",
        effects=(Effect("purchase_order", "update", gl="posts"),),
        invariants=("period_open",),
        risk="post",
        idempotency=("order_id",),
    ),
    Action(
        "pay_purchase_order",
        "Pay a billed purchase order — cash settlement against Accounts Payable (the user confirms "
        "by retyping the amount; posting is permanent). Use for 'pay PO <number>' or 'pay the order "
        "from <supplier>'. Defaults to the full outstanding balance; give an amount for a partial "
        "payment. Refused with no card if the order isn't billed yet, or if posting actions are "
        "turned off for this workspace.",
        {"query": "purchase order number or supplier name to find the order to pay",
         "amount": "optional amount in minor units — defaults to the full outstanding balance"},
        _build_pay_purchase_order, _execute_pay_purchase_order,
        kind="post",
        effects=(Effect("purchase_order", "update", gl="posts"),),
        invariants=("period_open",),
        risk="post",
        idempotency=("order_id", "amount_minor"),
    ),
    Action(
        "approve_purchase_request",
        "Approve a purchase request that is awaiting approval (the user confirms by retyping the "
        "amount; approving is permanent — it doesn't post to the GL or move stock, but it unlocks "
        "the request for conversion into a purchase order). Use for 'approve request <number>' or "
        "'approve the request from <supplier>'. Refused with no card if the request isn't awaiting "
        "approval, or if posting actions are turned off for this workspace.",
        {"query": "purchase request number or supplier name to find the request to approve"},
        _build_approve_purchase_request, _execute_approve_purchase_request,
        kind="approve",
        effects=(Effect("purchase_request", "update"),),
        risk="post",
        idempotency=("request_id",),
    ),
    Action(
        "issue_stock_entry",
        "Issue stock out of a warehouse — consumption that posts COGS (the user confirms by "
        "retyping the amount; posting is permanent). Use for 'issue <n> of <item> from "
        "<warehouse>' or 'use <n> of <item>'. Refused with no card if the quantity exceeds what's "
        "on hand, or if posting actions are turned off for this workspace.",
        {"item": "item sku or name to issue",
         "quantity": "quantity to issue",
         "warehouse": "optional warehouse code to issue from (defaults to the default warehouse)"},
        _build_issue_stock_entry, _execute_issue_stock_entry,
        kind="adjust",
        effects=(Effect("stock_movement", "create", stock="moves", gl="posts"),),
        invariants=("stock_non_negative", "period_open"),
        risk="post",
        idempotency=("item_sku", "warehouse_code", "quantity"),
    ),
    Action(
        "create_account",
        "Create a new chart-of-accounts entry (master-data edit, the user confirms). Use for "
        "'create an expense account called <name>'. Warns if a similar account already exists.",
        {"name": "the new account's name",
         "type": "asset, liability, equity, income or expense",
         "code": "optional account code (auto-assigned if omitted)",
         "parent": "optional parent account code or name"},
        _build_create_account, _execute_create_account,
    ),
    Action(
        "create_opportunity",
        "Create a new opportunity/deal for a customer (the user confirms). Use for "
        "'new opportunity for <customer>: <deal name>, worth <amount>'.",
        {"customer": "customer code or name",
         "name": "the opportunity/deal name",
         "value": "optional deal value in minor units",
         "expected_close": "optional expected close date (YYYY-MM-DD)"},
        _build_create_opportunity, _execute_create_opportunity,
    ),
    Action(
        "advance_opportunity_stage",
        "Move an opportunity to another stage in the pipeline (the user confirms). Use for "
        "'move opportunity <number> to <stage>'. Valid stages: qualifying, proposal, negotiation.",
        {"query": "opportunity number or name to find",
         "stage": "target stage (qualifying, proposal, negotiation)"},
        _build_advance_opportunity_stage, _execute_advance_opportunity_stage,
        kind="update",
    ),
    Action(
        "log_activity",
        "Log a call, email, meeting, task or note against a customer or opportunity (the user "
        "confirms). Use for 'log a call with <customer>: <note>'.",
        {"query": "customer code/name or opportunity number",
         "note": "the activity note text",
         "type": "optional activity type: call, email, meeting, task, or note (default note)"},
        _build_log_activity, _execute_log_activity,
    ),
]}

def _validate_action(a: Action) -> None:
    """Import-time guard: an invalid declaration fails the module load, never a runtime call."""
    assert a.requires_confirm or a.kind not in DESTRUCTIVE_KINDS, (
        f"action {a.name}: destructive kind '{a.kind}' must require confirmation")
    assert a.risk in RISK_LEVELS, f"action {a.name}: unknown risk '{a.risk}'"
    assert a.requires_confirm or a.risk not in ("post", "destructive"), (
        f"action {a.name}: risk '{a.risk}' must require confirmation")
    from erp.assistant.verifier import PACKS as _VERIFIER_PACKS
    for inv in a.invariants:
        assert isinstance(inv, str) and inv.strip(), (
            f"action {a.name}: invariant names must be non-empty strings")
        assert inv in _VERIFIER_PACKS, (
            f"action {a.name}: invariant '{inv}' is not a registered verifier pack")
    assert a.compensation is None or a.compensation in ACTIONS, (
        f"action {a.name}: compensation '{a.compensation}' is not a registered action")
    if any(e.gl == "posts" or e.stock == "moves" for e in a.effects):
        assert a.risk in ("post", "destructive"), (
            f"action {a.name}: a posting/moving effect demands risk 'post' or higher")
        assert a.invariants, (
            f"action {a.name}: a posting/moving effect demands at least one invariant")


for _a in ACTIONS.values():
    _validate_action(_a)

# Which loop-decision fields can feed an action argument (each action gets only the args it declares).
ACTION_ARG_FIELDS = ("customer", "items", "supplier", "warehouse", "from_low_stock", "query",
                    "item", "quantity", "from_warehouse", "to_warehouse", "reorder_point", "scope",
                    "lines", "date", "reference", "type", "code", "parent", "memo", "name",
                    "value", "expected_close", "stage", "note", "amount")


def catalog_text() -> str:
    """Compact description of the proposable actions for the planner prompt."""
    lines = ["Write actions you may PROPOSE (never execute — the user confirms a card):"]
    for a in ACTIONS.values():
        args = ", ".join(f"{k} ({v})" for k, v in a.args.items()) or "no arguments"
        lines.append(f"- {a.name}: {a.description} Arguments: {args} [risk: {a.risk}]")
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


def challenge(minor: int, currency: str = "EGP") -> dict:
    """The retype-confirm the UI shows for a risk="post" proposal: a human-readable label (reusing
    Money.format — no new formatting logic) plus the exact minor-unit target to match against."""
    from erp.accounting.domain.money import Money
    return {"label": Money(minor, currency).format(), "minor": minor}


def idempotency_key(name: str, payload: dict) -> str:
    """The natural retry key for a confirm (FILE_03 T3.1): sha256 over the action name + the
    payload values named by its declared ``idempotency`` tuple (L0). An action with no declared
    tuple (the safe default) keys over the whole payload, so it dedupes only exact repeats."""
    action = ACTIONS.get(name)
    keys = action.idempotency if action is not None else ()
    material = {k: payload.get(k) for k in keys} if keys else payload
    blob = json.dumps(material, sort_keys=True, default=str)
    return hashlib.sha256(f"{name}:{blob}".encode()).hexdigest()
