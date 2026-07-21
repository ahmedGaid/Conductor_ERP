"""Backfill Arabic names onto departments seeded before `name_ar` existed.

Mirrors `accounting/0014_backfill_arabic_names`: the map is a frozen snapshot of the department
specs in `seed_identity` as of this migration, and only blank `name_ar` values on rows whose English
name is still the seeded one are filled — a company that renamed a department keeps its own wording.
"""
from django.db import migrations

DEPARTMENTS = {
    "FIN": ("Finance", "المالية"),
    "SALES": ("Sales", "المبيعات"),
    "OPS": ("Operations", "العمليات"),
}


def forwards(apps, schema_editor):
    model = apps.get_model("identity", "Department")
    for code, (seeded_en, name_ar) in DEPARTMENTS.items():
        model.objects.filter(code=code, name=seeded_en, name_ar="").update(name_ar=name_ar)


def backwards(apps, schema_editor):
    """Clear only the Arabic names this migration set — the column itself is dropped by 0013."""
    model = apps.get_model("identity", "Department")
    for code, (seeded_en, name_ar) in DEPARTMENTS.items():
        model.objects.filter(code=code, name=seeded_en, name_ar=name_ar).update(name_ar="")


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0013_department_name_ar"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
