#!/usr/bin/env python
"""Fix Agent Controlling navigation - add to correct section."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.control_center.models_navigation import NavigationSection, NavigationItem

# List all sections
print("=== ALL SECTIONS ===")
for s in NavigationSection.objects.all().order_by('order'):
    count = NavigationItem.objects.filter(section=s).count()
    print(f"  ID {s.id}: {s.name} ({count} items)")

# Find the AI & LLM Konfiguration section
print("\n=== FINDING CORRECT SECTION ===")
ai_section = None

# First try to find by name
ai_section = NavigationSection.objects.filter(name__icontains='LLM').first()
if not ai_section:
    ai_section = NavigationSection.objects.filter(name__icontains='AI').first()

if ai_section:
    items = NavigationItem.objects.filter(section=ai_section)
    item_names = [i.name for i in items]
    print(f"Found: {ai_section.name} (ID: {ai_section.id})")
    print(f"  Items: {item_names[:5]}...")

if ai_section:
    # Check if Controlling exists in this section
    existing = NavigationItem.objects.filter(section=ai_section, name__icontains='Controlling').first()
    if existing:
        print(f"\n✅ Agent Controlling already exists in {ai_section.name}")
    else:
        # Find max order
        max_order = NavigationItem.objects.filter(section=ai_section).order_by('-order').first()
        new_order = (max_order.order + 1) if max_order else 10
        
        # Create new item
        item = NavigationItem.objects.create(
            section=ai_section,
            name='Agent Controlling',
            external_url='/control-center/controlling/',
            icon='bi-graph-up',
            order=new_order,
            is_active=True
        )
        print(f"\n✅ Created Agent Controlling in {ai_section.name} (order: {new_order})")

# Also check if it was added to wrong section (AI Engine)
wrong_items = NavigationItem.objects.filter(name__icontains='Controlling').exclude(section=ai_section)
for item in wrong_items:
    print(f"\n⚠️ Found in wrong section: {item.name} in {item.section.name}")
    item.delete()
    print(f"   Deleted from wrong section")
