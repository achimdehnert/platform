#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.bfagent.models import Llms
for l in Llms.objects.filter(is_active=True)[:10]:
    print(f"{l.id}: '{l.name}' | '{l.llm_name}'")
