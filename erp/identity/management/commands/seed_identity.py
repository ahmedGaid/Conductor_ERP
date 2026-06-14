"""Idempotent seed of RBAC roles, a default branch, and a demo user per role.

Run: python manage.py seed_identity
Re-running makes no duplicate rows. Demo passwords are for dev only.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from erp.core.models import Branch
from erp.identity.roles import ACCOUNTANT, AUDITOR, BRANCH_MANAGER, DEFAULT_ROLES, SYSTEM_ADMIN

User = get_user_model()

DEMO_PASSWORD = "Dev12345!"
DEMO_USERS = [
    ("admin", "admin@erp.local", SYSTEM_ADMIN, True),
    ("manager", "manager@erp.local", BRANCH_MANAGER, False),
    ("accountant", "accountant@erp.local", ACCOUNTANT, False),
    ("auditor", "auditor@erp.local", AUDITOR, False),
]


class Command(BaseCommand):
    help = "Seed RBAC roles, a default branch, and demo users (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        for role in DEFAULT_ROLES:
            Group.objects.get_or_create(name=role)

        branch, _ = Branch.objects.get_or_create(
            code="HQ", defaults={"name": "Headquarters"}
        )

        for username, email, role, is_super in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_staff": is_super, "is_superuser": is_super},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.branch = None if is_super else branch
                user.save()
            user.groups.set([Group.objects.get(name=role)])

        self.stdout.write(self.style.SUCCESS("identity seeded: roles, HQ branch, demo users"))
