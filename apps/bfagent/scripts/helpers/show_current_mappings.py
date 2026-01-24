#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Show ACTUAL database mappings"""
import os
import sys
import django
from pathlib import Path

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import PhaseAgentConfig, AgentAction

print("=" * 80)
print("CURRENT DATABASE MAPPINGS (PhaseAgentConfig)")
print("=" * 80)

all_configs = PhaseAgentConfig.objects.select_related('phase', 'agent').order_by('phase__name', 'agent__name')

for config in all_configs:
    action_count = AgentAction.objects.filter(agent=config.agent).count()
    print(f"\nPhase: {config.phase.name}")
    print(f"   Agent: {config.agent.name}")
    print(f"   Agent Type: {config.agent.agent_type}")
    print(f"   Actions: {action_count}")
    print(f"   Status: {'OK' if action_count > 0 else 'NO ACTIONS!'}")
    print(f"   DB ID: {config.id}")

print("\n" + "=" * 80)
