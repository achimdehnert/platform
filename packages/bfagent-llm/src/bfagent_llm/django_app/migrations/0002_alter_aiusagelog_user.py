"""Add related_name to AIUsageLog.user to prevent reverse accessor clash."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("django_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aiusagelog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bfllm_usage_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
