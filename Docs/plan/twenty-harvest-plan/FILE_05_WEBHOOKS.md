# SESSION 5 — Outbound Webhooks
# Files: erp/notifications/models.py + services + tasks (extend), erp/notifications/api/ (extend), erp/notifications/tests/, apps/web settings page (new), i18n locales

Twenty reference: webhooks are a first-class metadata entity — any record event can notify an
external system. For us: the cheapest integration primitive, and the rail Phase E (WhatsApp)
and accountant tooling will ride on.

---

## Before You Start

1. Open `erp/core/` events — the emit/subscribe mechanism and the event-name catalog. Webhooks
   OBSERVE these events; this session adds ZERO new event emissions.
2. Open the SSRF/scope audit helpers (shipped session 00 of delivery hardening; grep
   `erp/` for the URL-validation helper) → REUSE for subscription URLs.
3. Open `erp/notifications/` models + an existing Celery task → match idiom.
4. Open one settings page in `apps/web/src/pages/` → match the settings-page kit.

"Do not write anything yet."

---

## Task A — Models + service

```python
class WebhookSubscription:  # url, event names (list), secret, is_active, created_by, timestamps
class WebhookDelivery:      # subscription FK, event, payload (JSON), status, attempts,
                            # last_error, next_retry_at, created_at
```

Service contract fns (`create_subscription`, `update_`, `delete_`, `list_deliveries`) — RBAC:
admin-only. URL validation on create/update: https-or-http, public address space only (reuse
the SSRF helper — NO requests to private ranges/localhost).

## Task B — Delivery

- Core-event listener filters active subscriptions by event name → enqueue Celery task.
- Payload: `{event, occurred_at, entity, id, data}` — money as integer minor units, no secrets.
- Headers: `X-Conductor-Event`, `X-Conductor-Signature: sha256=HMAC(secret, body)`.
- Retries: exponential (1m/5m/30m/2h, max 5), then status `failed`. 10s timeout. Every attempt
  recorded on the delivery row.

## Task C — Settings UI + events catalog

Settings → "الويب هوكس / Webhooks": list + create/edit (URL, event multi-select from the
catalog, regenerate secret shown once), per-subscription recent deliveries with status chips +
"retry now". Designed empty state ("no subscriptions yet" + what webhooks are, one calm line).
Arabic term: confirm/add the canonical word in Identity System §6 BEFORE shipping.

## Task D — Tests

Signature correctness; retry schedule on failure; inactive subscription skipped; SSRF-blocked
URL rejected at create; payload money is integers.

---

## Smoke Test

- [ ] Create subscription in UI → confirm a sales-order confirm event POSTs a signed payload to
      a local test receiver
- [ ] Kill the receiver → delivery shows retrying, then failed after max attempts
- [ ] `http://127.0.0.1/…` subscription rejected with a human error
- [ ] `pytest erp/notifications` green; parity + tsc + gate03 green; brand checklist on the page

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_06_SAVED_VIEWS_BACKEND.md in a FRESH session.
```
