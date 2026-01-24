#!/usr/bin/env python
"""Fix invalid JSON in action_templates.pipeline_config before migration."""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import ActionTemplate

print("🔍 Checking action_templates.pipeline_config...")

for at in ActionTemplate.objects.all():
    if at.pipeline_config:
        try:
            # Try to parse as JSON
            json.loads(at.pipeline_config)
            print(f"✅ ID {at.id}: Valid JSON")
        except json.JSONDecodeError:
            print(f"❌ ID {at.id}: Invalid JSON - Setting to NULL")
            at.pipeline_config = None
            at.save(update_fields=['pipeline_config'])
    else:
        print(f"⚪ ID {at.id}: Empty/NULL (OK)")

print("\n✅ All pipeline_config fields fixed!")
