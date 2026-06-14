"""Structured JSON logging.

Every log entry carries timestamp, module, function, severity, correlation_id, and (when
present) error_code. Unstructured text logs are not used anywhere in the codebase.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging

from .correlation import get_correlation_id


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": _dt.datetime.fromtimestamp(
                record.created, tz=_dt.timezone.utc
            ).isoformat(),
            "severity": record.levelname,
            "module": getattr(record, "module_name", record.name),
            "function": record.funcName,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None) or get_correlation_id(),
        }
        error_code = getattr(record, "error_code", None)
        if error_code:
            payload["error_code"] = error_code
        error_id = getattr(record, "error_id", None)
        if error_id:
            payload["error_id"] = error_id
        if record.exc_info:
            payload["stack"] = self.formatException(record.exc_info)
        # Allow callers to attach arbitrary structured fields via `extra={"data": {...}}`.
        data = getattr(record, "data", None)
        if data is not None:
            payload["data"] = data
        return json.dumps(payload, ensure_ascii=False, default=str)
