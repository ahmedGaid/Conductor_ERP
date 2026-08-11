from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0014_agentrun_agentstep"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="active_stream_id",
            field=models.UUIDField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="conversation",
            name="last_stream_error",
            field=models.JSONField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="stream_id",
            field=models.UUIDField(blank=True, db_index=True, default=None, null=True),
        ),
    ]
