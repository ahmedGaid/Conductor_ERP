"""Money value object — integer minor units + ISO currency.

Money is NEVER a float in this system (binary floats can't represent 0.10 exactly, and accounting
must be exact). Amounts are stored and computed as integer **minor units** (piastres/cents); the
``Money`` type pairs that integer with its currency and forbids cross-currency arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass

# Egypt is the primary deployment (ETA e-invoicing, Africa/Cairo); EGP has 2 minor digits.
DEFAULT_CURRENCY = "EGP"
MINOR_UNIT_DIGITS = 2


class CurrencyMismatch(ValueError):
    """Raised when two Money values of different currencies are combined."""


@dataclass(frozen=True)
class Money:
    """An exact monetary amount: ``minor`` units of ``currency`` (e.g. 1050 == 10.50 EGP)."""

    minor: int
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        if not isinstance(self.minor, int) or isinstance(self.minor, bool):
            raise TypeError("Money.minor must be an int of minor units (no floats)")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be a 3-letter ISO code")

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> "Money":
        return cls(0, currency)

    def _check(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatch(f"{self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor + other.minor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.minor - other.minor, self.currency)

    @property
    def is_zero(self) -> bool:
        return self.minor == 0

    @property
    def is_negative(self) -> bool:
        return self.minor < 0

    def format(self) -> str:
        """Human string, e.g. 1050 -> '10.50' (display only; never used for math)."""
        scale = 10**MINOR_UNIT_DIGITS
        sign = "-" if self.minor < 0 else ""
        whole, frac = divmod(abs(self.minor), scale)
        return f"{sign}{whole}.{frac:0{MINOR_UNIT_DIGITS}d} {self.currency}"
