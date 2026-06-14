# Module Dependencies

> Allowed dependency directions. Business modules may depend on `core` (infrastructure) and
> communicate with each other only via events/contracts — never by importing internals.

```
core  <-  everything (infrastructure only)
identity, audit, monitoring  ->  core
workflow, forms              ->  core (+ events)
accounting, inventory, sales, purchasing, crm  ->  core, workflow (via contracts/events)
```

External runtime dependencies: PostgreSQL 16, Redis/Memurai (Celery broker + result backend).
