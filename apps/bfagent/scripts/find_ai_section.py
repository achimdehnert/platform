#!/usr/bin/env python
"""Find correct AI & LLM section and add Controlling."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.control_center.models_navigation import NavigationSection, NavigationItem

# Find section with LLMs verwalten
print("Looking for section with 'LLMs verwalten'...")
for s in NavigationSection.objects.all():
    items = list(NavigationItem.objects.filter(section=s).values_list('name', flat=True))
    if 'LLMs verwalten' in items:
        print(f"FOUND: Section ID {s.id}: {s.name}")
        print(f"  Items: {items}")
        
        # Add Controlling here
        if 'Agent Controlling' not in items:
            max_order = NavigationItem.objects.filter(section=s).order_by('-order').first()
            new_order = (max_order.order + 1) if max_order else 10
            NavigationItem.objects.create(
                section=s,
                name='Agent Controlling',
                external_url='/control-center/controlling/',
                icon='bi-graph-up',
                order=new_order,
                is_active=True
            )
            print(f"✅ Created Agent Controlling (order: {new_order})")
        else:
            print("✅ Agent Controlling already exists")
        break
else:
    print("Section not found")
    
# Delete from wrong section
print("\nChecking for items in wrong sections...")
wrong = NavigationItem.objects.filter(name='Agent Controlling').exclude(section__name__icontains='Konfiguration')
for item in wrong:
    print(f"Deleting from: {item.section.name}")
    item.delete()
