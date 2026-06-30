"""Universal entity search — the live backbone of the ⌘K command palette.

Charter R10 (keyboard-first): from one entry point, jump to any customer, supplier, item, sales
order, purchase order, or journal by **name or number**, in Arabic or English, tolerant of the way
people actually type Arabic (missing hamzas, ة/ه, ي/ى). ``GET /api/core/search?q=...`` →
``{"data": [{type, label, sublabel, to}, ...]}``.

Charter R2 (context respects permission): every type is gated by the module the user can reach
(``access.accessible_modules``), so a result never leaks a record from a module the user has no
access to. Conductor is single-tenant (customer-hosted), so there is no per-row org scoping.

Arabic folding here is a 1:1 mirror of ``apps/web/src/lib/arabicSearch.ts`` so the server matches
exactly what the client would — folding shapes the *comparison key only*, never the displayed text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from django.apps import apps
from django.db.models import Q
from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity import access

# --- Arabic-aware folding (mirror of arabicSearch.ts: foldArabic / normalizeSearch) -------------
_TASHKEEL = re.compile("[ً-ْٰ]")  # harakat, tanwin, shadda, sukun, dagger-alef
_TATWEEL = re.compile("ـ")  # kashida


def fold_arabic(s: str) -> str:
    """Fold Arabic letter variants to a single search form. Apply to BOTH sides of a comparison."""
    s = _TASHKEEL.sub("", s)
    s = _TATWEEL.sub("", s)
    s = re.sub("[أإآٱ]", "ا", s)  # أ إ آ ٱ → ا
    s = s.replace("ؤ", "و")  # ؤ → و
    s = re.sub("[ئي]", "ى", s)  # ئ ي → ى
    s = s.replace("ة", "ه")  # ة → ه
    s = s.replace("ء", "")  # bare hamza ء → drop
    return s


def normalize_search(s: str) -> str:
    """Canonical search key: lower-cased (Latin) + Arabic-folded."""
    return fold_arabic(s.lower())


# --- Searchable types ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SearchType:
    key: str  # public type tag; the client localizes it ('command.type.<key>')
    module: str  # gate: only searched if in access.accessible_modules(user)
    app_label: str
    model: str
    fields: tuple[str, ...]  # columns matched (raw icontains + folded scan)
    order: str  # queryset ordering for the bounded fold-scan
    label: Callable[[dict], str]  # row → primary display text
    sublabel: Callable[[dict], str]  # row → secondary text
    route: Callable[[dict], str]  # row → client path

    @property
    def columns(self) -> tuple[str, ...]:
        # Everything fetched: the id plus the searched/displayed fields, deduped, order preserved.
        return tuple(dict.fromkeys(("id", *self.fields)))


SEARCH_TYPES: tuple[SearchType, ...] = (
    SearchType(
        key="customer", module="sales", app_label="sales", model="Customer",
        fields=("code", "name"), order="name",
        label=lambda r: r["name"], sublabel=lambda r: r["code"],
        route=lambda r: f"/sales/customers/{r['code']}",
    ),
    SearchType(
        key="supplier", module="purchasing", app_label="purchasing", model="Supplier",
        fields=("code", "name"), order="name",
        label=lambda r: r["name"], sublabel=lambda r: r["code"],
        route=lambda r: f"/purchasing/suppliers/{r['code']}",
    ),
    SearchType(
        key="item", module="inventory", app_label="inventory", model="Item",
        fields=("sku", "name"), order="name",
        label=lambda r: r["name"], sublabel=lambda r: r["sku"],
        route=lambda r: f"/inventory/items/{r['sku']}",
    ),
    SearchType(
        key="sales_order", module="sales", app_label="sales", model="SalesOrder",
        fields=("number", "customer__name"), order="-created_at",
        label=lambda r: r["number"], sublabel=lambda r: r["customer__name"] or "",
        route=lambda r: f"/sales/orders/{r['id']}",
    ),
    SearchType(
        key="purchase_order", module="purchasing", app_label="purchasing", model="PurchaseOrder",
        fields=("number", "supplier__name"), order="-created_at",
        label=lambda r: r["number"], sublabel=lambda r: r["supplier__name"] or "",
        route=lambda r: f"/purchasing/orders/{r['id']}",
    ),
    SearchType(
        key="journal", module="accounting", app_label="accounting", model="JournalEntry",
        fields=("number",), order="-created_at",
        label=lambda r: r["number"], sublabel=lambda r: "",
        route=lambda r: f"/accounting/journals/{r['id']}",
    ),
)

_MIN_QUERY = 2  # below this, searching is noise
_PER_TYPE = 4  # max hits surfaced per type
_TOTAL = 12  # overall cap on a response
_SCAN_CAP = 400  # bounded window for the Arabic-fold fallback (SME single-tenant scale)


def _search_one(st: SearchType, raw_q: str, folded_q: str) -> list[dict]:
    """Hits for one type. Fast exact-script DB pass, then a bounded Arabic-fold fallback."""
    model = apps.get_model(st.app_label, st.model)
    rows: dict[str, dict] = {}

    # Pass 1 — DB icontains on the raw query. Covers numbers, codes, SKUs, Latin, and Arabic that
    # was typed in the same orthography as stored (the overwhelming common case), and stays indexed.
    cond = Q()
    for f in st.fields:
        cond |= Q(**{f + "__icontains": raw_q})
    for r in model.objects.filter(cond).order_by(st.order)[: _PER_TYPE * 3].values(*st.columns):
        rows[str(r["id"])] = r

    # Pass 2 — Arabic-fold fallback: only when pass 1 was thin, scan a bounded recent window and
    # match on the folded key so misspelled Arabic still finds the record.
    if len(rows) < _PER_TYPE:
        for r in model.objects.order_by(st.order)[:_SCAN_CAP].values(*st.columns):
            rid = str(r["id"])
            if rid in rows:
                continue
            if any(folded_q in normalize_search(str(r[f] or "")) for f in st.fields):
                rows[rid] = r
                if len(rows) >= _PER_TYPE * 3:
                    break

    out: list[dict] = []
    for r in list(rows.values())[:_PER_TYPE]:
        out.append({"type": st.key, "label": st.label(r), "sublabel": st.sublabel(r), "to": st.route(r)})
    return out


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        raw_q = (request.query_params.get("q") or "").strip()
        if len(raw_q) < _MIN_QUERY:
            return Response({"data": []})
        folded_q = normalize_search(raw_q)
        allowed = set(access.accessible_modules(request.user))

        results: list[dict] = []
        for st in SEARCH_TYPES:
            if st.module not in allowed:
                continue
            results.extend(_search_one(st, raw_q, folded_q))
            if len(results) >= _TOTAL:
                break
        return Response({"data": results[:_TOTAL]})


urlpatterns = [path("search", SearchView.as_view(), name="search")]
