"""Import adapters: finance documents — journal entries + GL opening balances (``erp.accounting``).

Both write DRAFT journal entries through the accounting module's ONLY sanctioned draft write-path,
``contracts.create_journal_entry_draft`` — the same balanced/postable-account invariants as a
posted entry, but the ledger is untouched until a human posts it from the journal screen
(STRATEGY §3 mechanic 3: imports create drafts, posting stays on module screens). Neither adapter
ever touches ``JournalEntry``/``JournalLine`` for a WRITE; each adapter's ``delete`` is the one
exception (rollback of a still-DRAFT entry — a plain ORM delete, which has posted nothing to the
ledger, so there is no module write-path to route a reversal through).

Two grouped (document) adapters:

* ``journal_entries`` — a flat file of many entries, one row per LINE, grouped by the source entry/
  voucher number. Each entry must balance (Σdebit == Σcredit) or the whole entry errors
  (``unbalanced_entry``) via the engine's ``validate_group`` hook — the rest of the file still
  imports (group atomicity, FILE_15).

* ``account_opening`` — a trial-balance snapshot for go-live: the WHOLE file becomes ONE balanced
  opening journal entry (grouped by a synthetic constant key — ``opening_ref`` defaults to
  ``"opening"`` so every row lands in one document). A file that doesn't balance is NOT silently
  forced: the adapter proposes a single balancing line to a configurable suspense account
  (``IMPORTS_DEFAULTS['account_opening']['suspense_account']``) and refuses to insert it until a
  human approves it explicitly (``batch.stats['opening_correction']['approved']``) — the roadmap
  Phase-A promise ("trial balance must balance or the import proposes the correcting entry"),
  delivered human-in-the-loop. Rendering that proposal and collecting the approval is the preview/
  creation-plan panel (apps/web — Agent A's territory); this file delivers the backend it reads.

DELIBERATELY NOT BUILT here (FILE_16 Before-You-Start STOP rule — no GL-correct, drafts-only module
write-path exists, so building them would misstate a customer's books; recorded in ``erp-status``):

* ``payments`` — the purchasing mirror of ``receipts`` below. This one is NO LONGER on this list:
  session 16b added ``erp.purchasing.services.pending_payments.create_pending_payment`` — a
  standalone, unallocated ``PendingPayment`` a payment can land in without touching the GL — and
  built the ``payments`` adapter against it in ``erp/imports/adapters/purchasing.py`` (not here;
  this file is ``erp.accounting`` adapters only).

  ``receipts`` (the sales-side twin of this same reasoning) is also NO LONGER on this list: session
  16b added ``erp.sales.services.pending_payments.create_pending_payment`` — a standalone,
  unallocated ``PendingPayment`` a receipt can land in without touching the GL — and built the
  ``receipts`` adapter against it in ``erp/imports/adapters/sales.py`` (not here).

* ``inventory_opening`` / ``inventory_transactions`` — ``inventory.receive`` posts Dr Inventory /
  Cr GRNI (a supplier-bill liability, wrong for an opening) and ``adjust_stock`` posts the offset to
  a P&L variance account; both post immediately and would DOUBLE-COUNT the Inventory control account
  that ``account_opening`` already books. Weighted-average costing carries no as-of-date, so
  replaying backdated historic movements computes cost against the CURRENT balance and corrupts
  COGS. No draft
  inventory-opening / sub-ledger-load service exists to import against.
"""
from __future__ import annotations

import datetime as _dt

from django.conf import settings

from erp.accounting import contracts
from erp.accounting.domain.models import EntryStatus, JournalEntry
from erp.identity.roles import ACCOUNTANT
from erp.identity.scoping import scope_queryset

from ..registry import FieldSpec, Issue, register
from ._rbac import require_role


# --- shared line/account resolution --------------------------------------------------------------
def _as_date(value) -> _dt.date | None:
    """A ``kind="date"`` field round-trips through ``ImportRow.normalized`` (a JSONField) as an ISO
    string — never a live ``datetime.date`` by the time ``write`` sees it (as in the sales
    adapters)."""
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str) and value:
        return _dt.date.fromisoformat(value)
    return None


def _find_account_code(value) -> str | None:
    """Resolve an account cell (a code like ``"1100"`` or a name like ``"Accounts Receivable"``) to
    a chart-of-accounts code, or ``None``. Exact code wins (indexed, the common case); a
    case-insensitive name match is the fallback. Postable/active is left to ``create_draft_journal``
    to enforce — the same single validation point every module posts through."""
    ref = str(value).strip() if value is not None else ""
    if not ref:
        return None
    info = contracts.find_account(ref)  # exact code
    if info is not None:
        return info.code
    lowered = ref.casefold()
    for account in contracts.list_accounts():
        if account.name.casefold() == lowered:
            return account.code
    return None


def _build_lines(group: dict) -> list:
    """One ``LineInput`` per non-blank line row. A row with neither debit nor credit is a trailing/
    blank line and is dropped (an all-zero line would fail ``post``'s one-side-positive rule and
    error the whole document for a cosmetic reason). Unknown account → raise, so the engine reports
    ``group_write_failed`` for that document only."""
    lines = []
    for line in group["lines"]:
        code = _find_account_code(line.get("account_ref"))
        if code is None:
            raise ValueError(f"unknown account: {line.get('account_ref')!r}")
        debit = int(line.get("debit_minor") or 0)
        credit = int(line.get("credit_minor") or 0)
        if debit == 0 and credit == 0:
            continue
        lines.append(contracts.LineInput(account_code=code, debit=debit, credit=credit,
                                         memo=(line.get("line_memo") or "")))
    return lines


def _totals(lines: list[dict]) -> tuple[int, int]:
    total_debit = sum(int(line.get("debit_minor") or 0) for line in lines)
    total_credit = sum(int(line.get("credit_minor") or 0) for line in lines)
    return total_debit, total_credit


def _write_entry(actor, group: dict, *, ref_prefix: str, source: str, group_key_field: str):
    ref = (group.get(group_key_field) or "").strip()
    data = contracts.JournalInput(
        date=_as_date(group.get("date")) or _dt.date.today(),
        lines=_build_lines(group),
        memo=group.get("memo") or "",
        reference=f"{ref_prefix}{ref}",
        source=source,
    )
    return contracts.create_journal_entry_draft(data, actor=actor)


def _exists(actor, group: dict, *, ref_prefix: str, group_key_field: str):
    ref = (group.get(group_key_field) or "").strip()
    if not ref:
        return None
    qs = scope_queryset(actor, JournalEntry.objects.all(), "accounting.journal.view")
    return qs.filter(reference=f"{ref_prefix}{ref}").first()


def _delete_draft(pk) -> None:
    """Rollback support: a DRAFT entry created by an import has posted nothing to the ledger, so a
    plain delete (lines cascade) is a true, side-effect-free reversal. Refuses if it moved past
    DRAFT since import (a human posted it) — never deletes a live ledger entry out from under
    them."""
    entry = JournalEntry.objects.filter(pk=pk).first()
    if entry is None:
        return  # already gone — rollback is idempotent
    if entry.status != EntryStatus.DRAFT:
        raise ValueError(
            f"cannot delete journal entry {entry.number}: status is {entry.status!r}, not draft"
        )
    entry.delete()


def _existing_labels(actor, ref_prefix: str) -> list[tuple]:
    qs = scope_queryset(
        actor, JournalEntry.objects.filter(reference__startswith=ref_prefix),
        "accounting.journal.view",
    )
    return list(qs.values_list("pk", "number"))


# --- field specs shared by both finance documents ------------------------------------------------
_ACCOUNT_FIELD = FieldSpec(
    name="account_ref", required=True, kind="ref", ref="accounts",
    synonyms_en=["account", "account code", "account name", "gl account"],
    synonyms_ar=["الحساب", "كود الحساب", "اسم الحساب", "رقم الحساب"],
)
_DEBIT_FIELD = FieldSpec(
    name="debit_minor", kind="money",
    synonyms_en=["debit", "dr", "debit amount"],
    synonyms_ar=["مدين", "المدين"],
)
_CREDIT_FIELD = FieldSpec(
    name="credit_minor", kind="money",
    synonyms_en=["credit", "cr", "credit amount"],
    synonyms_ar=["دائن", "الدائن"],
)


# --- journal_entries -----------------------------------------------------------------------------
class JournalEntryAdapter:
    """Flat journal file: one row per line, grouped by the source entry/voucher number. Header
    fields (number, date, memo) repeat or fill only the group's first row — the merged-cell pattern
    the group engine (FILE_15) already handles. Each entry must balance or the whole entry errors
    (``validate_group``), leaving the rest of the file to import."""

    entity = "journal_entries"
    label_key = "imports.entity.journalEntries"
    fields = [
        # --- header (one per entry; blank on continuation rows of the same group) ---
        FieldSpec(
            name="entry_ref", kind="text",
            synonyms_en=["entry number", "journal number", "voucher", "voucher no", "je no"],
            synonyms_ar=["رقم القيد", "رقم اليومية", "رقم السند"],
        ),
        FieldSpec(
            name="date", kind="date",
            synonyms_en=["date", "entry date"],
            synonyms_ar=["التاريخ", "تاريخ القيد"],
        ),
        FieldSpec(
            name="memo", kind="text",
            synonyms_en=["memo", "description", "narration", "statement"],
            synonyms_ar=["البيان", "الوصف", "الشرح"],
        ),
        # --- line (every row) ---
        _ACCOUNT_FIELD,
        _DEBIT_FIELD,
        _CREDIT_FIELD,
        FieldSpec(
            name="line_memo", kind="text",
            synonyms_en=["line description", "line memo", "note"],
            synonyms_ar=["بيان السطر", "ملاحظة"],
        ),
    ]
    natural_key = ["entry_ref"]
    group_by = "entry_ref"
    header_fields = ["entry_ref", "date", "memo"]

    _ref_prefix = "import-je:"

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "account_ref":
            return _find_account_code(value)
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def validate_group(self, actor, payload: dict, batch) -> list[Issue]:
        """Σdebit must equal Σcredit for the entry. An imbalance errors the whole entry with the
        money difference (formatted at the edge from ``difference_minor``) and is logged to a
        batch-level ``unbalanced_entries`` summary so a report can name every bad entry at once."""
        total_debit, total_credit = _totals(payload["lines"])
        if total_debit == total_credit:
            return []
        diff = total_debit - total_credit
        _append_stat(batch, "unbalanced_entries", {
            "entry_ref": (payload.get("entry_ref") or "").strip(),
            "difference_minor": diff,
        })
        return [Issue(
            field="", code="unbalanced_entry", message="imports.issues.unbalancedEntry",
            meta={"total_debit_minor": total_debit, "total_credit_minor": total_credit,
                  "difference_minor": diff},
        )]

    def write(self, actor, group: dict):
        require_role(actor, ACCOUNTANT)
        return _write_entry(actor, group, ref_prefix=self._ref_prefix, source="import",
                            group_key_field="entry_ref")

    def exists(self, actor, group: dict):
        return _exists(actor, group, ref_prefix=self._ref_prefix, group_key_field="entry_ref")

    def delete(self, actor, pk) -> None:
        _delete_draft(pk)

    def existing_labels(self, actor):
        return _existing_labels(actor, self._ref_prefix)


register(JournalEntryAdapter())


# --- account_opening -----------------------------------------------------------------------------
class AccountOpeningAdapter:
    """GL opening balances (a go-live trial balance): the WHOLE file becomes ONE balanced opening
    journal entry. ``opening_ref`` defaults to ``"opening"`` so every row groups into one document
    (a file may still split into several openings by giving distinct refs). When the file doesn't
    balance, ``validate_group`` proposes a single balancing line to a suspense account and blocks
    until a human approves it — never silently forced (Phase-A promise, human-in-the-loop)."""

    entity = "account_opening"
    label_key = "imports.entity.accountOpening"
    fields = [
        # --- header (one per entry; ``opening_ref`` defaults so a header-less file = 1 entry) ---
        FieldSpec(
            name="opening_ref", kind="text", default="opening",
            synonyms_en=["opening batch", "opening reference", "batch"],
            synonyms_ar=["مرجع الرصيد الافتتاحي", "الدفعة"],
        ),
        FieldSpec(
            name="date", kind="date",
            synonyms_en=["opening date", "date", "as of"],
            synonyms_ar=["تاريخ الرصيد الافتتاحي", "التاريخ", "كما في"],
        ),
        FieldSpec(
            name="memo", kind="text",
            synonyms_en=["memo", "description", "narration"],
            synonyms_ar=["البيان", "الوصف"],
        ),
        # --- line (every row) ---
        _ACCOUNT_FIELD,
        _DEBIT_FIELD,
        _CREDIT_FIELD,
    ]
    natural_key = ["opening_ref"]
    group_by = "opening_ref"
    header_fields = ["opening_ref", "date", "memo"]

    _ref_prefix = "import-open:"

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "account_ref":
            return _find_account_code(value)
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def validate_group(self, actor, payload: dict, batch) -> list[Issue]:
        """Balanced → proceed. Imbalanced → record the proposed suspense line in
        ``batch.stats['opening_correction']`` (what the creation-plan panel renders) and either
        BLOCK with ``opening_imbalance`` (until a human sets ``approved``) or, once approved, inject
        the balancing line into ``payload['lines']`` so ``write`` posts a balanced opening entry."""
        total_debit, total_credit = _totals(payload["lines"])
        diff = total_debit - total_credit
        if diff == 0:
            return []
        suspense = self.defaults.get("suspense_account") or "3100"
        if diff > 0:  # debits exceed credits → the balancing line is a CREDIT
            proposal = {"account_ref": suspense, "debit_minor": 0, "credit_minor": diff}
        else:  # credits exceed debits → the balancing line is a DEBIT
            proposal = {"account_ref": suspense, "debit_minor": -diff, "credit_minor": 0}

        approved = _record_correction(batch, total_debit, total_credit, diff, suspense, proposal)
        if not approved:
            return [Issue(
                field="", code="opening_imbalance", message="imports.issues.openingImbalance",
                meta={"difference_minor": diff, "suspense_account": suspense,
                      "proposed_line": proposal},
            )]
        payload["lines"].append(proposal)  # human-approved correction, consumed by write
        return []

    def write(self, actor, group: dict):
        require_role(actor, ACCOUNTANT)
        return _write_entry(actor, group, ref_prefix=self._ref_prefix, source="import-opening",
                            group_key_field="opening_ref")

    def exists(self, actor, group: dict):
        return _exists(actor, group, ref_prefix=self._ref_prefix, group_key_field="opening_ref")

    def delete(self, actor, pk) -> None:
        _delete_draft(pk)

    def existing_labels(self, actor):
        return _existing_labels(actor, self._ref_prefix)


register(AccountOpeningAdapter())


# --- batch.stats helpers (the HITL surface the preview/creation-plan panel reads) ----------------
def _append_stat(batch, key: str, item: dict) -> None:
    stats = dict(batch.stats or {})
    entries = list(stats.get(key, []))
    entries.append(item)
    stats[key] = entries
    batch.stats = stats
    batch.save(update_fields=["stats"])


def _record_correction(batch, total_debit: int, total_credit: int, diff: int,
                       suspense: str, proposal: dict) -> bool:
    """Persist (refresh) the opening-correction proposal on the batch, PRESERVING any ``approved``
    flag a human already set via the panel. Returns whether it is approved."""
    stats = dict(batch.stats or {})
    approved = bool((stats.get("opening_correction") or {}).get("approved"))
    stats["opening_correction"] = {
        "total_debit_minor": total_debit, "total_credit_minor": total_credit,
        "difference_minor": diff, "suspense_account": suspense,
        "proposed_line": proposal, "approved": approved,
    }
    batch.stats = stats
    batch.save(update_fields=["stats"])
    return approved
