#!/usr/bin/env python
"""Check master data tables"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import TargetAudience

print("=" * 80)
print("📊 MASTER DATA CHECK")
print("=" * 80)

# Target Audiences
print(f"\n✅ TARGET AUDIENCES: {TargetAudience.objects.count()} total")
for ta in TargetAudience.objects.all()[:10]:
    print(f"   - {ta}")

# Check if there are Themes
try:
    from django.apps import apps
    all_models = apps.get_models()
    theme_models = [m for m in all_models if 'theme' in m.__name__.lower()]
    
    if theme_models:
        print(f"\n✅ THEME MODELS FOUND:")
        for model in theme_models:
            print(f"   - {model.__name__}: {model.objects.count()} entries")
    else:
        print(f"\n⚠️  NO THEME MODELS FOUND")
except Exception as e:
    print(f"\n⚠️  Error checking themes: {e}")

print("\n" + "=" * 80)
