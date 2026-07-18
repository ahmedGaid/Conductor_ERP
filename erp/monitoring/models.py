"""Calm milestone moments (arp-roadmap track P, item 2).

One row per milestone the company has crossed and been shown. Company-wide, not per-user — a
single-tenant install has one "first profitable month", seen once by whoever's looking, dismissed
for everyone (matches the calm brand: quiet delight, not a per-login nag).
"""
from __future__ import annotations

from django.db import models


class MilestoneAck(models.Model):
    """A milestone the dashboard has shown (and someone dismissed), keyed by a stable string."""

    key = models.CharField(max_length=80, unique=True)
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitoring_milestone_ack"

    def __str__(self) -> str:  # pragma: no cover
        return self.key
