#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from apps.bfagent.models import BookProjects
print("Existing BookProjects:")
for p in BookProjects.objects.all():
    print(f"  {p.id}: {p.title}")
