"""Bank reconciliation: tie a bank statement to its cash/bank GL account.

Each statement line is matched to a posted GL journal line on the same cash account (auto by signed
amount, or manually). Bank-only items (fees, interest) are booked with an **adjustment journal** posted
through `post_journal`, which creates the GL line the statement line then matches. A statement is
**reconciled** when every statement line is matched, every in-range cash GL line is matched, and the
statement's closing balance equals the cash GL balance — i.e. nothing is outstanding.

Amounts are integer **minor units**. A statement line's `amount_minor` is signed: + increases cash
(deposit), − decreases it (withdrawal). A cash GL line's signed amount is `debit − credit`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Sum

from ..domain.models import (
    Account,
    BankStatement,
    BankStatementLine,
    BankStatementStatus,
    EntryStatus,
    JournalLine,
)
from ..errors import BankMatchError, NotACashAccountError, NotReconciledError
from .posting import JournalInput, LineInput, post_journal


@dataclass
class BankLineInput:
    date: object       # datetime.date
    amount_minor: int  # signed: + deposit / − withdrawal
    description: str = ""


def _cash_account(account_code: str) -> Account:
    account = Account.objects.filter(code=account_code).first()
    if account is None or not account.is_cash:
        raise NotACashAccountError(data={"account": account_code})
    return account


@transaction.atomic
def create_statement(*, account_code: str, statement_date, closing_balance_minor: int,
                     opening_balance_minor: int = 0, reference: str = "",
                     lines: list[BankLineInput] | None = None, actor=None) -> BankStatement:
    """Create a bank statement (validating the account is a cash/bank account) and its lines."""
    _cash_account(account_code)
    statement = BankStatement.objects.create(
        account_code=account_code,
        statement_date=statement_date,
        opening_balance_minor=opening_balance_minor,
        closing_balance_minor=closing_balance_minor,
        reference=reference,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    for i, line in enumerate(lines or [], start=1):
        BankStatementLine.objects.create(
            statement=statement, line_no=i, date=line.date,
            description=line.description, amount_minor=line.amount_minor,
        )
    return statement


def _matched_gl_line_ids() -> set[int]:
    """GL lines already claimed by some statement line (across all statements)."""
    return set(
        BankStatementLine.objects.filter(matched_line__isnull=False)
        .values_list("matched_line_id", flat=True)
    )


def _candidate_gl_lines(statement: BankStatement):
    """Unmatched posted cash GL lines on this account up to the statement date."""
    claimed = _matched_gl_line_ids()
    return (
        JournalLine.objects.filter(
            entry__status=EntryStatus.POSTED,
            account__code=statement.account_code,
            entry__date__lte=statement.statement_date,
        )
        .exclude(id__in=claimed)
        .select_related("entry")
    )


@transaction.atomic
def auto_match(statement: BankStatement) -> int:
    """Match each unmatched statement line to a cash GL line of equal signed amount. Returns count."""
    candidates = list(_candidate_gl_lines(statement))
    # Index unmatched candidates by signed amount (debit − credit).
    by_amount: dict[int, list[JournalLine]] = {}
    for gl in candidates:
        by_amount.setdefault(gl.debit - gl.credit, []).append(gl)

    matched = 0
    for line in statement.lines.filter(matched_line__isnull=True).order_by("line_no"):
        bucket = by_amount.get(line.amount_minor)
        if bucket:
            gl = bucket.pop(0)
            line.matched_line = gl
            line.save(update_fields=["matched_line"])
            matched += 1
    return matched


@transaction.atomic
def match_line(line: BankStatementLine, gl_line: JournalLine) -> BankStatementLine:
    """Manually match a statement line to a GL line (must be same account + equal signed amount)."""
    if gl_line.account.code != line.statement.account_code:
        raise BankMatchError(data={"reason": "account mismatch"})
    if (gl_line.debit - gl_line.credit) != line.amount_minor:
        raise BankMatchError(data={"reason": "amount mismatch"})
    if gl_line.id in _matched_gl_line_ids():
        raise BankMatchError(data={"reason": "ledger line already matched"})
    line.matched_line = gl_line
    line.save(update_fields=["matched_line"])
    return line


@transaction.atomic
def unmatch_line(line: BankStatementLine) -> BankStatementLine:
    line.matched_line = None
    line.save(update_fields=["matched_line"])
    return line


@transaction.atomic
def post_adjustment(statement: BankStatement, *, amount_minor: int, contra_account_code: str,
                    memo: str = "", date=None, actor=None) -> JournalLine:
    """Book a bank-only item (fee/interest) to the cash account, then match it to its statement line.

    ``amount_minor`` signed like a statement line: + increases cash (Dr Cash / Cr contra),
    − decreases cash (Dr contra / Cr Cash). Returns the created cash GL line.
    """
    if amount_minor == 0:
        raise BankMatchError(data={"reason": "adjustment amount is zero"})
    cash = statement.account_code
    if amount_minor > 0:
        lines = [LineInput(cash, debit=amount_minor), LineInput(contra_account_code, credit=amount_minor)]
    else:
        amt = -amount_minor
        lines = [LineInput(contra_account_code, debit=amt), LineInput(cash, credit=amt)]
    entry = post_journal(
        JournalInput(
            date=date or statement.statement_date,
            memo=memo or f"Bank adjustment — {cash}",
            reference=statement.reference or f"BANKADJ-{statement.id}",
            source="accounting.bank_rec",
            lines=lines,
        ),
        actor=actor,
    )
    cash_gl_line = entry.lines.get(account__code=cash)
    # Auto-match to an unmatched statement line of the same signed amount, if one exists.
    target = statement.lines.filter(matched_line__isnull=True, amount_minor=amount_minor).order_by("line_no").first()
    if target is not None:
        target.matched_line = cash_gl_line
        target.save(update_fields=["matched_line"])
    return cash_gl_line


@dataclass
class GLLineView:
    id: int
    date: str
    entry_number: str
    memo: str
    amount_minor: int  # signed (debit − credit)


@dataclass
class Reconciliation:
    account_code: str
    statement_date: str
    statement_closing: int
    book_balance: int          # cash GL signed balance as of the statement date
    difference: int            # statement_closing − book_balance
    unmatched_statement: list  # BankStatementLine-derived dicts
    unmatched_book: list       # GLLineView (outstanding ledger items)
    is_reconciled: bool
    status: str


def _book_balance(account_code: str, as_of) -> int:
    agg = (
        JournalLine.objects.filter(
            entry__status=EntryStatus.POSTED,
            account__code=account_code,
            entry__date__lte=as_of,
        )
        .aggregate(d=Sum("debit"), c=Sum("credit"))
    )
    return (agg["d"] or 0) - (agg["c"] or 0)


def reconciliation(statement: BankStatement) -> Reconciliation:
    """Compute the reconciliation: book vs statement, outstanding items, and the tie-out flag."""
    book_balance = _book_balance(statement.account_code, statement.statement_date)
    difference = statement.closing_balance_minor - book_balance

    unmatched_statement = [
        {"line_no": ln.line_no, "date": str(ln.date), "description": ln.description,
         "amount_minor": ln.amount_minor}
        for ln in statement.lines.filter(matched_line__isnull=True).order_by("line_no")
    ]
    unmatched_book = [
        GLLineView(
            id=gl.id, date=str(gl.entry.date), entry_number=gl.entry.number,
            memo=gl.memo or gl.entry.memo, amount_minor=gl.debit - gl.credit,
        )
        for gl in _candidate_gl_lines(statement).order_by("entry__date", "entry__number", "line_no")
    ]
    is_reconciled = (
        not unmatched_statement and not unmatched_book and difference == 0
    )
    return Reconciliation(
        account_code=statement.account_code,
        statement_date=str(statement.statement_date),
        statement_closing=statement.closing_balance_minor,
        book_balance=book_balance,
        difference=difference,
        unmatched_statement=unmatched_statement,
        unmatched_book=unmatched_book,
        is_reconciled=is_reconciled,
        status=statement.status,
    )


@transaction.atomic
def mark_reconciled(statement: BankStatement) -> BankStatement:
    """Lock the statement as reconciled — only if it strictly ties out to the cash ledger."""
    if not reconciliation(statement).is_reconciled:
        raise NotReconciledError(data={"statement": str(statement.id)})
    statement.status = BankStatementStatus.RECONCILED
    statement.save(update_fields=["status"])
    return statement
