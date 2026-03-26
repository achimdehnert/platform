"""
linkedin_oauth/migrations/0001_initial.py
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LinkedInToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)),
                ("tenant_id", models.BigIntegerField(db_index=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="linkedin_token",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("access_token", models.TextField()),
                ("refresh_token", models.TextField(blank=True, default="")),
                ("access_token_expires_at", models.DateTimeField()),
                ("refresh_token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("scope", models.CharField(blank=True, default="", max_length=512)),
                ("linkedin_urn", models.CharField(blank=True, default="", max_length=128)),
                ("linkedin_sub", models.CharField(blank=True, default="", max_length=128)),
                ("is_active", models.BooleanField(default=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "linkedin_oauth_token"},
        ),
        migrations.AddIndex(
            model_name="linkedintoken",
            index=models.Index(fields=["tenant_id", "user"], name="li_tenant_user_idx"),
        ),
        migrations.AddIndex(
            model_name="linkedintoken",
            index=models.Index(fields=["access_token_expires_at"], name="li_token_exp_idx"),
        ),
    ]
