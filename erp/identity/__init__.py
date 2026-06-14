"""identity — authentication, users, RBAC, 2FA, per-branch scoping.

Stage 0 ships a minimal custom User (so AUTH_USER_MODEL is fixed before the first migration).
Stage 1 expands it with JWT, roles/permissions, TOTP 2FA, and branch scoping.
"""
