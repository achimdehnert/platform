import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.control_center.models_navigation import NavigationItem
from django.urls import reverse, NoReverseMatch

print("=== Fixing Invalid Navigation URLs ===\n")

# List of URLs that exist in control_center
VALID_URLS = [
    'control_center:dashboard',
    'control_center:api-status',
    'control_center:api-tools',
    'control_center:metrics',
    'control_center:model-consistency',
    'control_center:screen-documentation',
    'control_center:genagent-dashboard',
    'control_center:feature-planning-dashboard',
    'control_center:migration-registry-dashboard',
    'control_center:code-review-dashboard',
]

all_items = NavigationItem.objects.filter(is_active=True)
deactivated = 0
kept = 0

for item in all_items:
    if not item.url_name:
        continue
        
    # Check if URL is valid
    try:
        if ':' in item.url_name and item.url_name.startswith('control_center:'):
            if item.url_name not in VALID_URLS:
                print(f"❌ Deactivating: {item.name} ({item.url_name})")
                item.is_active = False
                item.save()
                deactivated += 1
            else:
                print(f"✅ Keeping: {item.name} ({item.url_name})")
                kept += 1
        else:
            # Other namespaces - keep them
            kept += 1
    except Exception as e:
        print(f"⚠️  Error checking {item.name}: {e}")

print(f"\n✅ COMPLETE!")
print(f"   Deactivated: {deactivated}")
print(f"   Kept active: {kept}")
