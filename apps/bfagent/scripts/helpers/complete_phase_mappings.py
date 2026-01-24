#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Complete Phase-Agent Mappings for BF Agent"""
import os
import sys
import django

# Fix Windows Unicode
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import WorkflowPhase, Agents, PhaseAgentConfig

print("=" * 80)
print("COMPLETING PHASE-AGENT MAPPINGS")
print("=" * 80)

# Define mappings: Phase Name -> Agent Name
MAPPINGS = {
    "World Building": "World & Conflict Agent",
    "Editing": "Editor Agent",
    "Review": "Consistency Checker Agent",
    "Publishing": "Project Manager Agent",
    "Finalization": "Editorial Agent",
}

print("\n[*] Creating Phase-Agent Mappings...")

created = 0
skipped = 0
errors = 0

for phase_name, agent_name in MAPPINGS.items():
    try:
        # Get phase
        phase = WorkflowPhase.objects.get(name=phase_name)
        
        # Get agent
        agent = Agents.objects.get(name=agent_name)
        
        # Check if mapping already exists
        existing = PhaseAgentConfig.objects.filter(phase=phase, agent=agent).exists()
        
        if existing:
            print(f"   [SKIP] {phase_name} -> {agent_name} (already exists)")
            skipped += 1
        else:
            # Create mapping
            PhaseAgentConfig.objects.create(
                phase=phase,
                agent=agent,
                is_required=False,  # Optional by default
                order=0,  # Default order
                description=f"Auto-assigned agent for {phase_name} phase"
            )
            print(f"   [OK] Created: {phase_name} -> {agent_name}")
            created += 1
            
    except WorkflowPhase.DoesNotExist:
        print(f"   [ERROR] Phase not found: {phase_name}")
        errors += 1
    except Agents.DoesNotExist:
        print(f"   [ERROR] Agent not found: {agent_name}")
        errors += 1
    except Exception as e:
        print(f"   [ERROR] {phase_name} -> {agent_name}: {e}")
        errors += 1

print("\n" + "=" * 80)
print(f"[SUMMARY] Created: {created} | Skipped: {skipped} | Errors: {errors}")
print("=" * 80)

# Verify coverage
print("\n[*] Current Phase Coverage:")
all_phases = WorkflowPhase.objects.all().order_by('name')
total_phases = all_phases.count()
phases_with_agents = 0

for phase in all_phases:
    agent_count = PhaseAgentConfig.objects.filter(phase=phase).count()
    if agent_count > 0:
        phases_with_agents += 1
    status = "YES" if agent_count > 0 else "NO"
    print(f"   {phase.name}: {agent_count} agents [{status}]")

coverage = (phases_with_agents / total_phases * 100) if total_phases > 0 else 0
print(f"\n[COVERAGE] {phases_with_agents}/{total_phases} phases have agents ({coverage:.0f}%)")

if coverage == 100:
    print("\n[SUCCESS] All phases have agents assigned!")
else:
    print(f"\n[WARNING] {total_phases - phases_with_agents} phases still without agents")

print("\n" + "=" * 80)
print("[OK] PHASE-AGENT MAPPING COMPLETE")
print("=" * 80)
