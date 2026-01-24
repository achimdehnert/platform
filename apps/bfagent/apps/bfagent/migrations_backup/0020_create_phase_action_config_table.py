# Manual migration to fix missing phase_action_configs table
# Created on 2025-10-09 to fix issue where 0018 dropped table but 0019 didn't recreate it

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bfagent", "0019_add_agent_action_architecture"),
    ]

    operations = [
        # REMOVED: CreateModel 'PhaseActionConfig' (table 'phase_action_configs' already exists)
        # The CreateModel operations have been removed because tables already exist

    ]
