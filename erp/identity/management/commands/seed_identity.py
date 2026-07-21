"""Idempotent seed of RBAC roles, a default branch, org structure, and the admin user.

Run: python manage.py seed_identity                 # customer-safe: admin user only
     python manage.py seed_identity --demo-users    # ALSO seed non-admin demo users (dev only)

Re-running makes no duplicate rows. The default path is safe to run on a real customer
tenant: it provisions a single System Admin whose password the customer changes on first
login. The three non-admin demo accounts (manager/accountant/auditor) share a known dev
password and are created ONLY behind the explicit --demo-users flag.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from erp.core.models import Branch
from erp.identity.models import ApprovalLimit, Department, RolePermission, Team
from erp.identity.rbac import default_approval_limits, default_role_permissions
from erp.identity.roles import ACCOUNTANT, AUDITOR, BRANCH_MANAGER, DEFAULT_ROLES, SYSTEM_ADMIN

User = get_user_model()

DEMO_PASSWORD = "Dev12345!"

# The admin account is always seeded — a fresh tenant needs one login. Its password is a
# dev default the customer is told to change immediately (see Docs/RUNBOOK.md).
ADMIN_USER = ("admin", "admin@erp.local", SYSTEM_ADMIN, True)

# Non-admin demo accounts: dev convenience only, gated behind --demo-users. They share a
# known password, so they must never land on a customer tenant by default.
DEMO_USERS = [
    ("manager", "manager@erp.local", BRANCH_MANAGER, False),
    ("accountant", "accountant@erp.local", ACCOUNTANT, False),
    ("auditor", "auditor@erp.local", AUDITOR, False),
]

# Which demo users sit in which department (only applied when --demo-users is set).
DEMO_USER_DEPARTMENTS = [("accountant", "FIN"), ("manager", "SALES"), ("auditor", "FIN")]


class Command(BaseCommand):
    help = "Seed RBAC roles, a default branch, org structure, and the admin user (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo-users",
            action="store_true",
            help="Also seed the non-admin demo users (manager/accountant/auditor). "
            "Dev only — they share a known password; never use on a customer tenant.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        seed_demo_users = options["demo_users"]

        for role in DEFAULT_ROLES:
            Group.objects.get_or_create(name=role)

        branch, _ = Branch.objects.get_or_create(
            code="HQ", defaults={"name": "Headquarters", "name_ar": "المركز الرئيسي"}
        )

        # Org structure (departments + teams) for user management. Departments and branches are
        # reference records the user reads by name, so they seed with both names (erp/core/naming.py).
        dept_specs = [("FIN", "Finance", "المالية"), ("SALES", "Sales", "المبيعات"), ("OPS", "Operations", "العمليات")]
        departments = {}
        for code, name, name_ar in dept_specs:
            departments[code], _ = Department.objects.get_or_create(
                code=code, defaults={"name": name, "name_ar": name_ar, "branch": branch}
            )
        for code, name, dept_code in [("FIN-AP", "Accounts Payable", "FIN"), ("SALES-FIELD", "Field Sales", "SALES")]:
            Team.objects.get_or_create(
                code=code, defaults={"name": name, "department": departments[dept_code]}
            )

        users_to_seed = [ADMIN_USER]
        if seed_demo_users:
            users_to_seed += DEMO_USERS

        for username, email, role, is_super in users_to_seed:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_staff": is_super, "is_superuser": is_super},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.branch = None if is_super else branch
                user.save()
            user.groups.set([Group.objects.get(name=role)])

        # Place demo users in departments (idempotent, illustrative for the Users screen).
        if seed_demo_users:
            for username, dept_code in DEMO_USER_DEPARTMENTS:
                User.objects.filter(username=username).update(department=departments[dept_code])

        # Granular RBAC: grant each built-in role its default permission set + approval limits
        # (System Admin bypasses checks, so it carries no rows). Idempotent via update_or_create.
        for role_name, perms in default_role_permissions().items():
            group = Group.objects.get(name=role_name)
            for code, scope in perms:
                RolePermission.objects.update_or_create(
                    role=group, code=code, defaults={"scope": scope}
                )
        for role_name, limits in default_approval_limits().items():
            group = Group.objects.get(name=role_name)
            for document_type, limit_minor in limits.items():
                ApprovalLimit.objects.update_or_create(
                    role=group, document_type=document_type, defaults={"limit_minor": limit_minor}
                )

        seeded = "roles, HQ branch, admin user, role permissions"
        if seed_demo_users:
            seeded = "roles, HQ branch, admin + demo users, role permissions"
        self.stdout.write(self.style.SUCCESS(f"identity seeded: {seeded}"))
