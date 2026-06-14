"""REST adapter (stdlib urllib; no extra dependency).

Config: { method, url, headers?, body? }. Sends Idempotency-Key header when present. Maps HTTP
status to ok = 200..299. No retry here — retry/idempotency policy lives in the engine.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .types import AdapterCall, AdapterResult

DEFAULT_TIMEOUT = 10.0


class RestAdapter:
    kind = "rest"

    def call(self, call: AdapterCall) -> AdapterResult:
        cfg = call.config
        method = str(cfg.get("method", "GET")).upper()
        url = cfg["url"]
        headers = dict(cfg.get("headers") or {})
        body = cfg.get("body", call.payload)

        if call.idempotency_key:
            headers["Idempotency-Key"] = call.idempotency_key

        data = None
        if method not in ("GET", "HEAD") and body is not None:
            data = json.dumps(body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8") or "null"
                status = resp.status
                parsed = _maybe_json(raw)
                return AdapterResult(ok=200 <= status < 300, data=parsed, status=status)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace") if exc.fp else ""
            return AdapterResult(ok=False, data=_maybe_json(raw), error=str(exc), status=exc.code)
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(ok=False, error=f"{type(exc).__name__}: {exc}")


def _maybe_json(raw: str):
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw
