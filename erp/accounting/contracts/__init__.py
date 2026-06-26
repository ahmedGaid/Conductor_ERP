"""Public contract for the accounting module.

This is the ONLY surface other modules (Sales, Purchasing, ...) may import from. They post to the
ledger via ``post_journal(JournalInput(...))`` and react to ``JOURNAL_POSTED`` on the event bus —
never by importing accounting's ORM models or internals directly.
"""
from __future__ import annotations

from ..domain.money import DEFAULT_CURRENCY, Money
from ..events import JOURNAL_POSTED, PERIOD_CLOSED
from ..services.posting import JournalInput, LineInput, post_journal, reverse_journal
from ..services.seeding import baseline_summary, seed_baseline_accounting
from ..services.taxes import TaxCodeInfo, compute_tax, find_tax_code

__all__ = [
    "Money",
    "DEFAULT_CURRENCY",
    "JournalInput",
    "LineInput",
    "post_journal",
    "reverse_journal",
    "TaxCodeInfo",
    "compute_tax",
    "find_tax_code",
    "JOURNAL_POSTED",
    "PERIOD_CLOSED",
    "seed_baseline_accounting",
    "baseline_summary",
]
