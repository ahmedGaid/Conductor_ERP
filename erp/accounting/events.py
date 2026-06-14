"""Domain events published by the accounting module (consumed via the core event bus)."""
from __future__ import annotations

# Published after a journal entry is successfully posted to the ledger.
JOURNAL_POSTED = "accounting.JournalPosted"
# Published when a period is closed (locks further posting to it).
PERIOD_CLOSED = "accounting.PeriodClosed"
