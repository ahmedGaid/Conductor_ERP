import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_idempotencykey'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppliedUpgradeStep',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=128)),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'core_applied_upgrade_step',
                'ordering': ['applied_at'],
                'unique_together': {('version', 'name')},
            },
        ),
    ]
