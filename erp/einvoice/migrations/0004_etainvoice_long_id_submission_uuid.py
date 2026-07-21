# Generated for einvoice-eta-live FILE_02 — real ETA submission adapter.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('einvoice', '0003_etasettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='etainvoice',
            name='long_id',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='etainvoice',
            name='submission_uuid',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
    ]
