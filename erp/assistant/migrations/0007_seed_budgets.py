# ai-reliability T2.7: seed the three budget scopes from their settings defaults so enforcement
# has real rows from the first request — see config/settings/base.py's ASSISTANT_BUDGET_* comment
# for how these numbers were chosen. Idempotent (get_or_create) and never overwrites a value an
# admin already changed on a re-run.
from django.conf import settings
from django.db import migrations


def seed_budgets(apps, schema_editor):
    Budget = apps.get_model('assistant', 'Budget')
    action = getattr(settings, 'ASSISTANT_BUDGET_ACTION_DEFAULT', 'block')
    defaults = (
        ('request', getattr(settings, 'ASSISTANT_BUDGET_REQUEST_MICROCENTS', 50_000)),
        ('user', getattr(settings, 'ASSISTANT_BUDGET_USER_DAY_MICROCENTS', 500_000)),
        ('org', getattr(settings, 'ASSISTANT_BUDGET_ORG_MONTH_MICROCENTS', 300_000_000)),
    )
    for scope, limit_microcents in defaults:
        Budget.objects.get_or_create(
            scope=scope, defaults={'limit_microcents': limit_microcents, 'action': action},
        )


def unseed_budgets(apps, schema_editor):
    Budget = apps.get_model('assistant', 'Budget')
    Budget.objects.filter(scope__in=('request', 'user', 'org')).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0006_budget_spendrollup'),
    ]

    operations = [
        migrations.RunPython(seed_budgets, unseed_budgets),
    ]
