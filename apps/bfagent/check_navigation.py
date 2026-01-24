import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.control_center.models_navigation import NavigationSection, NavigationItem
from apps.bfagent.models_domains import DomainArt

print("=== Checking Navigation Items for Control Center ===\n")

try:
    control_center = DomainArt.objects.get(slug='control-center')
    print(f"✅ Found domain: {control_center.display_name}\n")
    
    sections = NavigationSection.objects.filter(domain_id=control_center, is_active=True)
    print(f"Found {sections.count()} sections:\n")
    
    for section in sections:
        print(f"\n📁 Section: {section.name}")
        items = NavigationItem.objects.filter(section=section, is_active=True)
        print(f"   Items: {items.count()}")
        
        for item in items:
            print(f"   - {item.name}")
            print(f"     URL Name: {item.url_name}")
            if item.url_params:
                print(f"     URL Params: {item.url_params}")
            
except DomainArt.DoesNotExist:
    print("❌ Control Center domain not found!")
