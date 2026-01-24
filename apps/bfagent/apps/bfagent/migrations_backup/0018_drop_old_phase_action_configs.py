# Manual migration to drop incompatible phase_action_configs table

from django.db import migrations


def drop_old_table(apps, schema_editor):
    """Drop the old string-based phase_action_configs table"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS phase_action_configs")


class Migration(migrations.Migration):
    dependencies = [
        ("bfagent", "0017_add_phase_agent_config"),
    ]

    operations = [
        migrations.RunPython(drop_old_table, reverse_code=migrations.RunPython.noop),
    ]
