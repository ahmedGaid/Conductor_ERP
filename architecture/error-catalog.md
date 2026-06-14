# Error Catalog

> Every known, catalogued error: code, description, module, file, function, likely causes, fix.
> Runtime errors also get a unique Error ID (`ERR-YYYY-NNNNNN`) for privacy-safe remote diagnosis.

| Code | Description | Module | File · Function | Likely cause | Recommended fix |
|---|---|---|---|---|---|
| GEN-001 | Validation failed | core | errors.py · ValidationError | Bad request payload | Correct the input per the API contract |
| GEN-002 | Resource not found | core | errors.py · NotFoundError | Wrong id / deleted record | Verify the identifier |
| GEN-003 | Conflict | core | errors.py · ConflictError | State conflict (e.g. wrong workflow node) | Retry against current state |
| GEN-004 | Permission denied / IP not allowed | core | errors.py · PermissionError; middleware.py · IpWhitelistMiddleware | RBAC or IP whitelist | Grant role / whitelist the IP |
| GEN-500 | Internal server error | core | exceptions.py · drf_exception_handler | Unhandled exception | Use the Error ID + correlation ID to locate the structured log |

> Module-specific codes (e.g. `WF-001 Approval node not found`) are added by each module as it lands.
