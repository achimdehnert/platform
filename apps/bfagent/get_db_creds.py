#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings

db = settings.DATABASES['default']
print(f"HOST={db.get('HOST')}")
print(f"NAME={db.get('NAME')}")
print(f"USER={db.get('USER')}")
print(f"PASSWORD={db.get('PASSWORD')}")
print(f"PORT={db.get('PORT')}")
