"""The installed license — a single row (pk=1), same shape as ``identity.OrgPreferences``."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class InstalledLicense(models.Model):
    """What key (if any) this install has, and when the trial/first boot happened.

    ``key_text`` empty = no key installed (trial or unmanaged, depending on ``LICENSE_MODE``).
    """

    key_text = models.TextField(blank=True, default="")
    installed_at = models.DateTimeField(null=True, blank=True)
    installed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    # Trial start — set once, on the first time current_state() ever runs against this DB.
    first_run_at = models.DateTimeField(null=True, blank=True)
    # Last date the app was seen running — clock-rollback detection lives in FILE_03; this file
    # only carries the column so that later increment doesn't need a migration of its own.
    last_seen_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "installed license"
        verbose_name_plural = "installed license"

    def __str__(self) -> str:  # pragma: no cover
        return "installed license" if self.key_text else "installed license (no key)"
