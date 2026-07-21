"""Backfill the Arabic name onto the branch seeded before `name_ar` existed.

Same rule as `accounting/0014_backfill_arabic_names`: only a blank `name_ar` on a row still carrying
the seeded English name is filled, so a company that renamed its head office keeps its own wording.
"""
from django.db import migrations

BRANCHES = {
    "HQ": ("Headquarters", "المركز الرئيسي"),
}


def forwards(apps, schema_editor):
    model = apps.get_model("core", "Branch")
    for code, (seeded_en, name_ar) in BRANCHES.items():
        model.objects.filter(code=code, name=seeded_en, name_ar="").update(name_ar=name_ar)


def backwards(apps, schema_editor):
    """Clear only the Arabic name this migration set — the column itself is dropped by 0005."""
    model = apps.get_model("core", "Branch")
    for code, (seeded_en, name_ar) in BRANCHES.items():
        model.objects.filter(code=code, name=seeded_en, name_ar=name_ar).update(name_ar="")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_branch_name_ar_alter_customfielddef_entity_key"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
