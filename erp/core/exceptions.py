"""DRF exception handling.

Turns errors into a consistent ``{"error": {...}}`` envelope that always includes an
error_id and correlation_id, logs them structurally, and never leaks internals to the client.
"""
from __future__ import annotations

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from .correlation import get_correlation_id
from .errors import AppError, new_error_id

logger = logging.getLogger("erp.core")


def drf_exception_handler(exc: Exception, context: dict) -> Response | None:
    correlation_id = get_correlation_id()

    if isinstance(exc, AppError):
        logger.warning(
            exc.message,
            extra={"error_code": exc.code, "error_id": exc.error_id, "data": exc.data},
        )
        return Response(
            {"error": {**exc.to_dict(), "correlation_id": correlation_id}},
            status=exc.status_code,
        )

    # Let DRF handle its own known exceptions, then wrap the envelope.
    response = drf_default_handler(exc, context)
    if response is not None:
        error_id = new_error_id()
        response.data = {
            "error": {
                "error_id": error_id,
                "code": "HTTP-%s" % response.status_code,
                "message": response.data,
                "correlation_id": correlation_id,
            }
        }
        return response

    # Unknown/unhandled: log with stack, return a privacy-safe envelope.
    error_id = new_error_id()
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        extra={"error_code": "GEN-500", "error_id": error_id},
    )
    return Response(
        {
            "error": {
                "error_id": error_id,
                "code": "GEN-500",
                "message": "Internal server error",
                "correlation_id": correlation_id,
            }
        },
        status=500,
    )
