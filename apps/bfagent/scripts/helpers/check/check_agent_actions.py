#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check which agents have actions"""
import os
import sys
import django
from pathlib import Path

# Fix Windows Unicode
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import Agents, AgentAction, PhaseAgentConfig

print("=" * 80)
print("AGENT ACTIONS AUDIT")
print("=" * 80)

# Get all agents
all_agents = Agents.objects.all().order_by('name')

print(f"\n[*] Total Agents: {all_agents.count()}\n")

for agent in all_agents:
    action_count = AgentAction.objects.filter(agent=agent).count()
    phase_count = PhaseAgentConfig.objects.filter(agent=agent).count()
    
    status = "OK" if action_count > 0 else "NO ACTIONS"
    symbol = "[OK]" if action_count > 0 else "[!!]"
    
    print(f"{symbol} {agent.name}")
    print(f"   Type: {agent.agent_type}")
    print(f"   Actions: {action_count}")
    print(f"   Assigned to Phases: {phase_count}")
    
    if action_count > 0:
        actions = AgentAction.objects.filter(agent=agent).values_list('display_name', flat=True)
        for action in actions[:3]:
            print(f"      - {action}")
        if action_count > 3:
            print(f"      ... and {action_count - 3} more")
    print()

# Summary
agents_with_actions = Agents.objects.filter(actions__isnull=False).distinct().count()
agents_without_actions = all_agents.count() - agents_with_actions

print("=" * 80)
print(f"[SUMMARY] {agents_with_actions} agents with actions | {agents_without_actions} without actions")
print("=" * 80)
