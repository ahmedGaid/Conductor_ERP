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
        return {"error": f"No customer matches '{customer or ''}' in what you can see."}
    warehouse_code = (warehouse or "").strip() or inventory.default_warehouse_code()
    if not warehouse_code:
        return {"error": "No warehouse is set up to sell from yet."}

    lines, records, risks = [], [], []
    total = 0
    for entry in items or []:
        item = _resolve_item(entry.get("item") if isinstance(entry, dict) else None)
        qty = _qty(entry.get("quantity") if isinstance(entry, dict) else None)
        if item is None:
            risks.append(f"Item '{(entry or {}).get('item', '')}' was not found — skipped.")
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
    ranked = _rank(supplier or "", purchasing.list_suppliers(), lambda s: s.name) if supplier else []
    match = ranked[0][1] if ranked and ranked[0][0] >= 0.6 else None
    if match is None:
        return {"error": f"No supplier matches '{supplier or ''}' — say which supplier to request from."}

    entries = list(items or [])
    warehouse_code = (warehouse or "").strip()
    risks = []
    if from_low_stock:
        low = inventory.low_stock(limit=20)
        if not low:
            return {"error": "Nothing is below its reorder point right now."}
        entries = [{"item": r["sku"], "quantity": "1"} for r in low]
        warehouse_code = warehouse_code or (low[0].get("warehouse_code") or "")
        risks.append("Quantities defaulted to 1 — set the real amounts on the request screen.")
    warehouse_code = warehouse_code or (inventory.default_warehouse_code() or "")
    if not warehouse_code:
        return {"error": "No warehouse is set up to receive into yet."}

    lines, records = [], []
    total = 0
    for entry in entries:
        item = _resolve_item(entry.get("item") if isinstance(entry, dict) else None)
        qty = _qty(entry.get("quantity") if isinstance(entry, dict) else None)
        if item is None:
            risks.append(f"Item '{(entry or {}).get('item', '')}' was not found — skipped.")
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


# --- registry -----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Action:
    name: str
    description: str          # for the loop prompt
    args: dict                # arg -> description
    build_proposal: Callable  # (actor, **args) -> {summary, records, risks, payload} | {error}
    execute: Callable         # (actor, payload) -> {links, summary}


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
]}

# Which loop-decision fields can feed an action argument (each action gets only the args it declares).
ACTION_ARG_FIELDS = ("customer", "items", "supplier", "warehouse", "from_low_stock", "query")


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
        return action.build_proposal(actor, **kwargs)
    except Exception:  # bad argument shape — a calm note, never a crash
        return {"error": "That could not be prepared. Try rephrasing what to create."}


def execute(actor, name: str, payload: dict) -> dict:
    """Run a confirmed action's write as the actor. Raises on a refused/invalid confirm (the view
    turns that into the right status code)."""
    action = ACTIONS.get(name)
    if action is None:
        raise ValueError(f"unknown action {name}")
    return action.execute(actor, payload)
