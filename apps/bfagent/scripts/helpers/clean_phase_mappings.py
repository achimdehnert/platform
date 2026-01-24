#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Clean up Phase-Agent mappings - Remove agents WITHOUT actions"""
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

from apps.bfagent.models import PhaseAgentConfig, AgentAction

print("=" * 80)
print("CLEANING PHASE-AGENT MAPPINGS")
print("=" * 80)

# Get all phase-agent configs
all_configs = PhaseAgentConfig.objects.select_related('phase', 'agent').all()

print(f"\n[*] Total PhaseAgentConfig entries: {all_configs.count()}\n")

removed = 0
kept = 0

for config in all_configs:
    agent = config.agent
    phase = config.phase
    
    # Check if agent has any actions
    action_count = AgentAction.objects.filter(agent=agent).count()
    
    if action_count == 0:
        print(f"[REMOVE] {phase.name} -> {agent.name} (0 actions)")
        config.delete()
        removed += 1
    else:
        print(f"[KEEP] {phase.name} -> {agent.name} ({action_count} actions)")
        kept += 1

print("\n" + "=" * 80)
print(f"[SUMMARY] Removed: {removed} | Kept: {kept}")
print("=" * 80)

# Show current status
from apps.bfagent.models import WorkflowPhase

print("\n[*] Updated Phase Coverage:")
all_phases = WorkflowPhase.objects.all().order_by('name')
for phase in all_phases:
    agent_count = PhaseAgentConfig.objects.filter(phase=phase).count()
    print(f"   {phase.name}: {agent_count} agents")

print("\n" + "=" * 80)
print("[OK] CLEANUP COMPLETE")
print("=" * 80)
