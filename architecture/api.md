# API

> Endpoint inventory per module. All responses use a consistent envelope; errors carry
> `error_id` + `correlation_id`. Full OpenAPI/Swagger is generated during hardening (Stage 7).

| Method | Path | Module | Auth | Purpose |
|---|---|---|---|---|
| GET | /health | monitoring | none | Liveness |
| GET | /system-check | monitoring | none | DB/Redis/storage/workers status |
| POST | /api/identity/login | identity | none | Login → JWT pair, or `{twofa_required}` |
| POST | /api/identity/token/refresh | identity | refresh token | Rotate access token |
| GET | /api/identity/me | identity | JWT | Current user + roles + branch |
| POST | /api/identity/2fa/provision | identity | JWT | Generate TOTP secret → otpauth URI |
| POST | /api/identity/2fa/enable | identity | JWT | Verify code, enable 2FA |
| GET | /api/identity/sample/finance | identity | JWT + role | RBAC demo (Accountant/Branch Manager) |
