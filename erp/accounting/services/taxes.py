"""Tax (VAT) services — code lookup + exact integer tax computation.

Tax is computed on a net amount in integer minor units: ``tax = round(net * rate_bps / 10000)``
with banker-free half-up rounding, so there is no float in the money path.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ..domain.models import TaxCode


@dataclass(frozen=True)
class TaxCodeInfo:
    code: str
    name: str
    rate_bps: int
    output_account_code: str
    input_account_code: str


def find_tax_code(code: str) -> TaxCodeInfo | None:
    tc = TaxCode.objects.filter(code=code, is_active=True).first()
    if tc is None:
        return None
    return TaxCodeInfo(code=tc.code, name=tc.name, rate_bps=tc.rate_bps,
                       output_account_code=tc.output_account_code,
                       input_account_code=tc.input_account_code)


def compute_tax(net_minor: int, code: str) -> int:
    """VAT on a net amount (minor units) for the given tax code. Unknown/zero code → 0."""
    info = find_tax_code(code)
    if info is None or info.rate_bps == 0:
        return 0
    return int((Decimal(net_minor) * Decimal(info.rate_bps) / Decimal(10000))
               .quantize(Decimal("1"), rounding=ROUND_HALF_UP))
