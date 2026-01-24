#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check Book Writing Phases Status"""
import os
import sys
import django

# CRITICAL: Fix Windows Unicode Issues
if sys.platform == "win32":
    # Force UTF-8 encoding for Windows console
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import (
    WorkflowPhase, 
    Agents, 
    AgentAction, 
    PromptTemplate, 
    BookProjects,
    PhaseAgentConfig,
    PhaseActionConfig
)

print("=" * 80)
print("BOOK WRITING SYSTEM STATUS")
print("=" * 80)

# 1. Workflow Phases
print("\n[*] WORKFLOW PHASES:")
phases = WorkflowPhase.objects.all().order_by('name')
print(f"   Total: {phases.count()}")
for phase in phases:
    print(f"   - {phase.name}")
    print(f"      Description: {phase.description[:60] if phase.description else 'N/A'}...")
    # Count agents via PhaseAgentConfig
    agent_count = PhaseAgentConfig.objects.filter(phase=phase).count()
    print(f"      Agents: {agent_count}")

# 2. Agents by Type
print("\n[*] AGENTS BY TYPE:")
agent_types = Agents.objects.values_list('agent_type', flat=True).distinct()
for agent_type in agent_types:
    agents = Agents.objects.filter(agent_type=agent_type)
    print(f"   {agent_type}: {agents.count()} agents")
    for agent in agents[:5]:
        actions_count = agent.actions.count()
        print(f"      - {agent.name} ({actions_count} actions)")

# 3. Actions with Templates
print("\n[*] ACTIONS WITH PROMPT TEMPLATES:")
actions = AgentAction.objects.select_related('agent', 'prompt_template').all()
print(f"   Total Actions: {actions.count()}")
actions_with_templates = actions.filter(prompt_template__isnull=False)
print(f"   Actions with Templates: {actions_with_templates.count()}")

print("\n   Sample Actions:")
for action in actions_with_templates[:10]:
    template_vars = "{{ context }}" in action.prompt_template.template_text
    print(f"      - {action.display_name}")
    print(f"        Agent: {action.agent.name}")
    print(f"        Template: {action.prompt_template.name}")
    print(f"        Has Context Variables: {'YES' if template_vars else 'NO'}")

# 4. Test Project Analysis
print("\n[*] TEST PROJECT ANALYSIS:")
test_projects = BookProjects.objects.all()[:3]
for project in test_projects:
    print(f"   Project: {project.title}")
    print(f"      Genre: {project.genre}")
    print(f"      Status: {project.status}")
    # Current phase is tracked via ProjectPhaseHistory
    current_phase = project.phase_history.filter(exited_at__isnull=True).first()
    phase_name = current_phase.phase.name if current_phase and current_phase.phase else 'None'
    print(f"      Current Phase: {phase_name}")
    print(f"      Chapters: {project.chapters.count()}")
    print(f"      Characters: {project.characters.count()}")

# 5. Coverage Analysis
print("\n[*] COVERAGE ANALYSIS:")
print(f"   Total Phases: {WorkflowPhase.objects.count()}")
print(f"   Total Agents: {Agents.objects.count()}")
print(f"   Total Actions: {AgentAction.objects.count()}")
print(f"   Total Prompt Templates: {PromptTemplate.objects.count()}")

# Check phase-agent connections via PhaseAgentConfig
phases_with_agents = PhaseAgentConfig.objects.values('phase').distinct().count()
total_phase_agent_configs = PhaseAgentConfig.objects.count()
total_phases = WorkflowPhase.objects.count()
phases_without_agents = total_phases - phases_with_agents
print(f"\n   Phases with Agents: {phases_with_agents}/{total_phases}")
print(f"   Total Phase-Agent Configs: {total_phase_agent_configs}")

# Check which agents have actions
agents_with_actions = Agents.objects.filter(actions__isnull=False).distinct().count()
agents_without_actions = Agents.objects.filter(actions__isnull=True).count()
print(f"\n   Agents with Actions: {agents_with_actions}")
print(f"   Agents without Actions: {agents_without_actions}")

# Check which actions have templates
actions_with_templates_count = AgentAction.objects.filter(prompt_template__isnull=False).count()
actions_without_templates = AgentAction.objects.filter(prompt_template__isnull=True).count()
print(f"\n   Actions with Templates: {actions_with_templates_count}")
print(f"   Actions without Templates: {actions_without_templates}")

print("\n" + "=" * 80)
print("[OK] STATUS CHECK COMPLETE")
print("=" * 80)
