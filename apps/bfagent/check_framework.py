#!/usr/bin/env python
"""Check framework structure"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.graph_core.models import Framework, FrameworkPhase, FrameworkStep

fw = Framework.objects.get(slug='vier-schichten-architektur')
print(f'Framework: {fw.name}')
print(f'ID: {fw.id}')
print()

for phase in fw.phases.all().order_by('order'):
    print(f'Phase {phase.order}: {phase.name} (ID: {phase.id})')
    for step in phase.steps.all().order_by('order'):
        print(f'  Step {step.order}: {step.name}')
