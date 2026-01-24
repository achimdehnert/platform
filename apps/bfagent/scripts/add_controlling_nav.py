#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fügt Agent Controlling zur Navigation hinzu."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.control_center.models_navigation import NavigationSection, NavigationItem

# Find AI & LLM section
section = NavigationSection.objects.filter(name__icontains='AI').first()
if section:
    print(f'Found section: {section.name} (ID: {section.id})')
    
    # Check existing items
    items = NavigationItem.objects.filter(section=section).order_by('order')
    print('Existing items:')
    for item in items:
        print(f'  - {item.name} (order: {item.order})')
    
    # Add Controlling if not exists
    existing = NavigationItem.objects.filter(section=section, name__icontains='Controlling').first()
    if not existing:
        max_order = items.last().order if items.exists() else 0
        new_item = NavigationItem.objects.create(
            section=section,
            name='Agent Controlling',
            external_url='/control-center/controlling/',
            icon='bi-graph-up',
            order=max_order + 1,
            is_active=True
        )
        print(f'✅ Created: {new_item.name}')
    else:
        print(f'ℹ️ Already exists: {existing.name}')
else:
    print('❌ AI section not found')
