"""Domain events published by the purchasing module."""
from __future__ import annotations

PO_APPROVED = "purchasing.OrderApproved"
PO_CONFIRMED = "purchasing.OrderConfirmed"
PO_RECEIVED = "purchasing.OrderReceived"
PO_BILLED = "purchasing.OrderBilled"
PO_PAID = "purchasing.OrderPaid"
PO_RETURNED = "purchasing.OrderReturned"
PR_SUBMITTED = "purchasing.RequestSubmitted"
PR_APPROVED = "purchasing.RequestApproved"
PR_REJECTED = "purchasing.RequestRejected"
PR_CONVERTED = "purchasing.RequestConverted"
