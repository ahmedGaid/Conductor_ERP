"""Import adapter: contacts (``erp.crm`` — the ``Lead`` model).

The codebase has no standalone "Contact" model; ``Lead`` (name/company/email/phone/source/owner) is
the CRM module's contact record, so "contacts" imports as leads. Writes go through
``erp.crm.contracts.create_lead``, which already stamps the actor's branch/department/team — the
same scoping every other CRM write gets, by construction.
"""
from __future__ import annotations

from django.conf import settings

from erp.crm import contracts
from erp.crm.domain.models import Lead, LeadSource
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset

from ..registry import FieldSpec, Issue, batch_lookup_code_or_name, register
from ._rbac import require_role


class ContactAdapter:
    entity = "contacts"
    label_key = "imports.entity.contacts"
    fields = [
        FieldSpec(
            name="name", required=True, kind="text",
            synonyms_en=["name", "contact name", "contact"],
            synonyms_ar=["الاسم", "اسم جهة الاتصال"],
        ),
        FieldSpec(
            name="company", kind="text",
            synonyms_en=["company", "organization"],
            synonyms_ar=["الشركة", "المؤسسة"],
        ),
        FieldSpec(
            name="email", kind="text",
            synonyms_en=["email", "e-mail"],
            synonyms_ar=["البريد الإلكتروني", "الايميل"],
        ),
        FieldSpec(
            name="phone", kind="text",
            synonyms_en=["phone", "mobile", "telephone"],
            synonyms_ar=["الهاتف", "الموبايل", "رقم الهاتف"],
        ),
        FieldSpec(
            name="source", kind="enum", enum=[c.value for c in LeadSource],
            synonyms_en=["source", "lead source"],
            synonyms_ar=["المصدر"],
        ),
        FieldSpec(
            name="owner", kind="text",
            synonyms_en=["owner", "assigned to"],
            synonyms_ar=["المسؤول", "المندوب"],
        ),
    ]
    natural_key = ["email", "name"]
    group_by = None

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        return None  # no ref fields on this entity

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        require_role(actor, BRANCH_MANAGER)
        lead = contracts.create_lead(
            name=row["name"],
            company=row.get("company", "") or "",
            email=row.get("email", "") or "",
            phone=row.get("phone", "") or "",
            source=row.get("source") or self.defaults.get("source", "other"),
            owner=row.get("owner", "") or "",
            actor=actor,
        )
        return lead

    def exists(self, actor, row: dict):
        qs = scope_queryset(actor, Lead.objects.all(), "crm.lead.view")
        email = (row.get("email") or "").strip()
        if email:
            return qs.filter(email__iexact=email).first()
        return qs.filter(name__iexact=(row.get("name") or "").strip()).first()

    def exists_many(self, actor, rows: list[dict]) -> list[Lead | None]:
        qs = scope_queryset(actor, Lead.objects.all(), "crm.lead.view")
        return batch_lookup_code_or_name(qs, rows, code_field="email", code_case_insensitive=True)

    def existing_labels(self, actor):
        qs = scope_queryset(actor, Lead.objects.all(), "crm.lead.view")
        return list(qs.values_list("pk", "name"))


register(ContactAdapter())
