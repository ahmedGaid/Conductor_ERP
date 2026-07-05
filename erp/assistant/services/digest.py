"""Ambient AI morning digest — one message per user, composed from the same read tools the
assistant answers questions with (DECISIONS "AI 2026-07": tool-use, never a parallel data path).

Runs AS the user (tools respect the actor), so a digest only ever contains what that user could
already ask the assistant for. Silence is the default: a digest must earn its send — an all-quiet
dataset sends nothing (Telegram calm, no "all good!" spam).
"""
from __future__ import annotations

import datetime

from erp.identity import access
from erp.identity.services import effective_preferences
from erp.notifications.domain.models import NotificationChannel
from erp.notifications.services import dispatch

from ..tools import _expiring_batches, _low_stock, _open_purchase_orders, _overdue_receivables

# How long a purchase order may sit open before the digest calls it "stuck".
STUCK_PO_DAYS = 14
# Rows shown inline per section; the header states the real total.
TOP_N = 3

_ROUTES = {
    "receivables": "/sales/customers",
    "low_stock": "/inventory/stock-on-hand",
    "batches": "/inventory/batches",
    "purchase_orders": "/purchasing",
}

_TEXT = {
    "en": {
        "subject": "Your morning digest",
        "receivables": "Overdue receivables — {count} customer(s), {total} outstanding:",
        "low_stock": "Low stock — {count} item(s) at or below reorder point:",
        "batches": "Batches expiring within 7 days — {count}:",
        "purchase_orders": "Purchase orders open more than {days} days — {count}:",
        "see_all": "See all: {route}",
    },
    "ar": {
        "subject": "ملخصك الصباحي",
        "receivables": "مستحقات متأخرة — {count} عميل، إجمالي {total}:",
        "low_stock": "مخزون منخفض — {count} صنف عند حد الطلب أو أقل:",
        "batches": "دفعات تنتهي خلال 7 أيام — {count}:",
        "purchase_orders": "أوامر شراء مفتوحة لأكثر من {days} يوم — {count}:",
        "see_all": "عرض الكل: {route}",
    },
}


def _lang(actor) -> str:
    return effective_preferences(actor).get("preferred_language") or "ar"


def _section(key: str, lang: str, header: str, rows: list[str]) -> str:
    route = _ROUTES[key]
    lines = [header] + [f"- {r}" for r in rows] + [_TEXT[lang]["see_all"].format(route=route)]
    return "\n".join(lines)


def _receivables_section(actor, lang: str) -> str | None:
    if not access.has_permission(actor, "sales.order.view"):
        return None
    r = _overdue_receivables(actor, limit=25)
    customers = r["customers"]
    if not customers:
        return None
    header = _TEXT[lang]["receivables"].format(count=len(customers), total=r["total_outstanding"])
    rows = [f"{c['name']} — {c['outstanding']}" for c in customers[:TOP_N]]
    return _section("receivables", lang, header, rows)


def _low_stock_section(actor, lang: str) -> str | None:
    if not access.has_permission(actor, "inventory.item.view"):
        return None
    items = _low_stock(actor, limit=50)["items"]
    if not items:
        return None
    header = _TEXT[lang]["low_stock"].format(count=len(items))
    rows = [f"{i['name']} ({i['sku']}) — {i['quantity']} @ {i['warehouse_code']}" for i in items[:TOP_N]]
    return _section("low_stock", lang, header, rows)


def _batches_section(actor, lang: str) -> str | None:
    if not access.has_permission(actor, "inventory.item.view"):
        return None
    batches = _expiring_batches(actor, days=7)["batches"]
    if not batches:
        return None
    header = _TEXT[lang]["batches"].format(count=len(batches))
    rows = [f"{b['name']} ({b['batch_no']}) — {b['expiry_date']}" for b in batches[:TOP_N]]
    return _section("batches", lang, header, rows)


def _purchase_orders_section(actor, lang: str) -> str | None:
    if not access.has_permission(actor, "purchasing.order.view"):
        return None
    today = datetime.date.today()
    orders = _open_purchase_orders(actor, limit=20)["orders"]
    stuck = [o for o in orders if (today - datetime.date.fromisoformat(o["order_date"])).days > STUCK_PO_DAYS]
    if not stuck:
        return None
    stuck.sort(key=lambda o: o["order_date"])
    header = _TEXT[lang]["purchase_orders"].format(count=len(stuck), days=STUCK_PO_DAYS)
    rows = [f"{o['number']} — {o['supplier_name']} — {o['outstanding']}" for o in stuck[:TOP_N]]
    return _section("purchase_orders", lang, header, rows)


def build_digest(actor) -> dict | None:
    """Compose the morning digest for one user from existing tool runners, run AS the user.

    Sections (each skipped when empty): overdue receivables, low stock, batches expiring within 7
    days, purchase orders stuck over ``STUCK_PO_DAYS``. Returns ``None`` when every section is
    empty — a digest must earn its send.
    """
    lang = _lang(actor)
    sections = [
        s for s in (
            _receivables_section(actor, lang),
            _low_stock_section(actor, lang),
            _batches_section(actor, lang),
            _purchase_orders_section(actor, lang),
        )
        if s is not None
    ]
    if not sections:
        return None
    return {"subject": _TEXT[lang]["subject"], "body": "\n\n".join(sections)}


def send_digests() -> int:
    """Build + dispatch the digest for every active, opted-in user. Returns the count sent.

    A user is due today if their preference is ``daily``, or ``weekly`` and today is Monday — the
    task itself decides due-ness (same shape as the accounting scheduled-report sweep), so the
    Celery beat entry just has to fire this once a day. Dispatch failures already land as ``failed``
    notification rows (``dispatch`` never raises) — never raise here either.
    """
    from erp.identity.models import User

    wanted = ["daily"] + (["weekly"] if datetime.date.today().weekday() == 0 else [])
    users = User.objects.filter(is_active=True, preferences__digest_frequency__in=wanted)

    sent = 0
    for user in users:
        digest = build_digest(user)
        if digest is None:
            continue
        dispatch(channel=NotificationChannel.INAPP, recipient=user.username,
                 subject=digest["subject"], body=digest["body"],
                 event_name="assistant.MorningDigest", actor=user)
        if user.email:
            dispatch(channel=NotificationChannel.EMAIL, recipient=user.email,
                     subject=digest["subject"], body=digest["body"],
                     event_name="assistant.MorningDigest", actor=user)
        sent += 1
    return sent
