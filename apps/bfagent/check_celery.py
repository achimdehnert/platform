#!/usr/bin/env python
"""Quick check of Celery configuration"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings

print("=== Celery Configuration ===")
print(f"CELERY_BROKER_URL: {getattr(settings, 'CELERY_BROKER_URL', 'NOT SET')}")
print(f"CELERY_RESULT_BACKEND: {getattr(settings, 'CELERY_RESULT_BACKEND', 'NOT SET')}")
print(f"Settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
