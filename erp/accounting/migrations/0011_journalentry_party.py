# Party dimension on journal entries: who the entry is with (customer/supplier).
from django.db import migrations, models


def backfill_party(apps, schema_editor):
    """Seed the party of pre-existing sales/purchasing entries so the new GL filter sees them.

    The ``reference`` holds the originating order number, so we resolve the party authoritatively
    from the order (codes may contain spaces, so memo-parsing is unreliable). Falls back to the
    ``" — <code>"`` memo suffix for the odd entry whose order can't be found (e.g. a reversal whose
    reference is a journal number). Going forward the party is stamped at posting time; this only
    backfills history. Untagged manual/inventory entries stay blank.
    """
    JournalEntry = apps.get_model("accounting", "JournalEntry")
    SalesOrder = apps.get_model("sales", "SalesOrder")
    PurchaseOrder = apps.get_model("purchasing", "PurchaseOrder")
    # source -> (party_type, {order number -> party code})
    customers = {o.number: o.customer.code for o in SalesOrder.objects.select_related("customer")}
    suppliers = {o.number: o.supplier.code for o in PurchaseOrder.objects.select_related("supplier")}
    by_source = {"sales": ("customer", customers), "purchasing": ("supplier", suppliers)}

    updated = []
    qs = JournalEntry.objects.filter(source__in=by_source.keys(), party_code="")
    for entry in qs.only("id", "source", "reference", "memo").iterator():
        party_type, code_by_order = by_source[entry.source]
        code = code_by_order.get(entry.reference)
        if not code and " — " in (entry.memo or ""):  # fallback for non-order references
            code = entry.memo.rsplit(" — ", 1)[1].strip() or None
        if not code:
            continue
        entry.party_type = party_type
        entry.party_code = code
        updated.append(entry)
    JournalEntry.objects.bulk_update(updated, ["party_type", "party_code"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0010_account_department_account_team_and_more"),
        # The backfill resolves the party from the originating order.
        ("sales", "0006_customer_department_customer_team_and_more"),
        ("purchasing", "0006_purchaseorder_department_purchaseorder_team_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="journalentry",
            name="party_type",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="journalentry",
            name="party_code",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["party_type", "party_code"], name="accounting__party_t_165fa5_idx"),
        ),
        migrations.RunPython(backfill_party, migrations.RunPython.noop),
    ]
