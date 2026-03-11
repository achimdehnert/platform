"""Create notification_log table (ADR-088)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NotificationLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(max_length=64, db_index=True),
                ),
                (
                    "channel",
                    models.CharField(max_length=50),
                ),
                (
                    "recipient",
                    models.CharField(max_length=255),
                ),
                (
                    "subject",
                    models.CharField(
                        blank=True, default="", max_length=255
                    ),
                ),
                ("body", models.TextField()),
                (
                    "source_app",
                    models.CharField(max_length=50),
                ),
                (
                    "source_event",
                    models.CharField(max_length=100),
                ),
                (
                    "metadata",
                    models.JSONField(default=dict),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "retry_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "sent_at",
                    models.DateTimeField(
                        blank=True, null=True
                    ),
                ),
            ],
            options={
                "db_table": "notification_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="notificationlog",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="idx_notif_tenant_status",
            ),
        ),
        migrations.AddIndex(
            model_name="notificationlog",
            index=models.Index(
                fields=["channel", "status"],
                name="idx_notif_channel_status",
            ),
        ),
        migrations.AddIndex(
            model_name="notificationlog",
            index=models.Index(
                fields=["source_app", "source_event"],
                name="idx_notif_source",
            ),
        ),
        migrations.AddIndex(
            model_name="notificationlog",
            index=models.Index(
                fields=["created_at"],
                name="idx_notif_created",
            ),
        ),
    ]
