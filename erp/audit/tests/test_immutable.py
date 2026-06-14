"""Audit entries are append-only: no updates, no deletes."""
from __future__ import annotations

import pytest

from erp.audit import services as audit
from erp.audit.models import AuditEntry


@pytest.mark.django_db
def test_record_writes_entry_with_correlation():
    from erp.core.correlation import correlation_scope

    with correlation_scope("CID-AUDIT"):
        entry = audit.record(
            module="test", action="create", entity_type="Thing", entity_id=1, after={"a": 1}
        )
    assert entry.pk is not None
    assert entry.correlation_id == "CID-AUDIT"


@pytest.mark.django_db
def test_update_is_blocked():
    entry = audit.record(module="test", action="create", entity_type="Thing", entity_id=1)
    entry.action = "tamper"
    with pytest.raises(ValueError):
        entry.save()


@pytest.mark.django_db
def test_delete_is_blocked():
    entry = audit.record(module="test", action="create", entity_type="Thing", entity_id=1)
    with pytest.raises(ValueError):
        entry.delete()
