"""Identity models.

A custom User is the auth principal. RBAC is implemented with Django's Group/Permission system
(a Group == a role, e.g. "Accountant", "Branch Manager"); endpoints enforce roles via the DRF
permission classes in ``permissions.py``. TOTP 2FA fields live on the user; the verification flow
is in ``services.py``.
"""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Email is the primary credential; username kept for admin compatibility.
    email = models.EmailField(unique=True)

    # Per-branch scoping. Null for org-wide roles (e.g. System Admin).
    branch = models.ForeignKey(
        "core.Branch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )

    # TOTP 2FA.
    is_2fa_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=64, blank=True, default="")

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "identity_user"

    def __str__(self) -> str:  # pragma: no cover
        return self.email or self.username

    @property
    def roles(self) -> list[str]:
        """Role names (Django groups) assigned to this user."""
        return list(self.groups.values_list("name", flat=True))
