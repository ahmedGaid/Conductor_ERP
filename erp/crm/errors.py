"""CRM error catalog (CRM-NNN)."""
from __future__ import annotations

from erp.core.errors import AppError


class InvalidTransitionError(AppError):
    code = "CRM-001"
    status_code = 422
    message = "Invalid CRM record status transition"


class LeadAlreadyConvertedError(AppError):
    code = "CRM-002"
    status_code = 422
    message = "Lead has already been converted"


class UnknownCustomerError(AppError):
    code = "CRM-003"
    status_code = 422
    message = "Opportunity references a customer that does not exist in Sales"


class EmptyOpportunityError(AppError):
    code = "CRM-004"
    status_code = 422
    message = "An opportunity needs at least one line to win into a sales order"


class AlreadyEscalatedError(AppError):
    code = "CRM-005"
    status_code = 409
    message = "Ticket has already been escalated"


class NotBreachedError(AppError):
    code = "CRM-006"
    status_code = 422
    message = "Ticket has not breached its SLA, so it cannot be escalated"
