"""Domain events published by the sales module."""
from __future__ import annotations

ORDER_APPROVED = "sales.OrderApproved"
ORDER_CONFIRMED = "sales.OrderConfirmed"
ORDER_DELIVERED = "sales.OrderDelivered"
ORDER_INVOICED = "sales.OrderInvoiced"
ORDER_RETURNED = "sales.OrderReturned"
PAYMENT_RECEIVED = "sales.PaymentReceived"
QUOTATION_SUBMITTED = "sales.QuotationSubmitted"
QUOTATION_APPROVED = "sales.QuotationApproved"
QUOTATION_REJECTED = "sales.QuotationRejected"
QUOTATION_CONVERTED = "sales.QuotationConverted"
