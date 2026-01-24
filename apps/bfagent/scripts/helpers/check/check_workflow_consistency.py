"""
Workflow Consistency Checker
Prüft ob für jede Phase Actions, Templates und Agents existieren
"""

import os
import sys

import django

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.bfagent.models import (
    AgentAction,
    Agents,
    PhaseActionConfig,
    PromptTemplate,
    WorkflowPhase,
)

print("=" * 80)
print("🔍 WORKFLOW CONSISTENCY CHECK")
print("=" * 80)

# 1. CHECK: Alle Phasen
phases = WorkflowPhase.objects.all().order_by("order")
print(f"\n📊 Found {phases.count()} Workflow Phases:")
for phase in phases:
    print(f"  - {phase.order}. {phase.name}")

print("\n" + "=" * 80)
print("🎯 PHASE → ACTION → TEMPLATE → AGENT CHECK")
print("=" * 80)

issues = []
recommendations = []

for phase in phases:
    print(f"\n{'=' * 80}")
    print(f"📌 PHASE: {phase.name} (Order: {phase.order})")
    print("=" * 80)

    # Check Phase Actions
    phase_configs = PhaseActionConfig.objects.filter(phase=phase).select_related(
        "action__agent", "action__prompt_template"
    )

    if not phase_configs.exists():
        issue = f"❌ Phase '{phase.name}' has NO actions configured!"
        print(f"  {issue}")
        issues.append(issue)
        recommendations.append(f"  → Create PhaseActionConfig for phase: {phase.name}")
        continue

    print(f"  ✅ Found {phase_configs.count()} action(s) for this phase")

    for i, config in enumerate(phase_configs, 1):
        action = config.action
        print(f"\n  {i}. ACTION: {action.display_name} (order: {config.order})")
        print(f"     Internal Name: {action.name}")
        print(f"     Required: {'✅ YES' if config.is_required else '⚠️  NO'}")

        # Check Agent
        if action.agent:
            print(f"     Agent: ✅ {action.agent.name}")
        else:
            issue = f"❌ Action '{action.display_name}' has NO agent assigned!"
            print(f"     Agent: {issue}")
            issues.append(issue)
            recommendations.append(f"  → Assign an agent to action: {action.display_name}")

        # Check Template
        if action.prompt_template:
            print(
                f"     Template: ✅ {action.prompt_template.name} (v{action.prompt_template.version})"
            )
        else:
            warning = f"⚠️  Action '{action.display_name}' has NO prompt template!"
            print(f"     Template: {warning}")
            issues.append(warning)
            recommendations.append(f"  → Create PromptTemplate for action: {action.display_name}")

print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)

# Count stats
total_phases = phases.count()
phases_with_actions = PhaseActionConfig.objects.values("phase").distinct().count()
total_actions = AgentAction.objects.count()
actions_with_templates = AgentAction.objects.filter(prompt_template__isnull=False).count()
actions_with_agents = AgentAction.objects.filter(agent__isnull=False).count()

print(f"\n📈 Statistics:")
print(f"  Total Phases: {total_phases}")
print(f"  Phases with Actions: {phases_with_actions}/{total_phases}")
print(f"  Total Actions: {total_actions}")
print(f"  Actions with Agents: {actions_with_agents}/{total_actions}")
print(f"  Actions with Templates: {actions_with_templates}/{total_actions}")

print(f"\n🔍 Issues Found: {len(issues)}")
if issues:
    print("\n❌ ISSUES:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("  ✅ No critical issues found!")

print(f"\n💡 RECOMMENDATIONS ({len(recommendations)}):")
if recommendations:
    for rec in recommendations:
        print(rec)
else:
    print("  ✅ Everything looks good!")

# Detailed Action Report
print("\n" + "=" * 80)
print("📋 DETAILED ACTION REPORT")
print("=" * 80)

all_actions = (
    AgentAction.objects.all()
    .select_related("agent", "prompt_template")
    .order_by("agent__name", "order")
)

for action in all_actions:
    status_agent = "✅" if action.agent else "❌"
    status_template = "✅" if action.prompt_template else "⚠️ "
    status_active = "✅" if action.is_active else "⚠️ "

    print(f"\n{action.display_name}")
    print(f"  Agent: {status_agent} {action.agent.name if action.agent else 'NONE'}")
    print(
        f"  Template: {status_template} {action.prompt_template.name if action.prompt_template else 'NONE'}"
    )
    print(f"  Active: {status_active}")
    print(f"  Used in Phases: {PhaseActionConfig.objects.filter(action=action).count()}")

print("\n" + "=" * 80)
print("✅ CHECK COMPLETE")
print("=" * 80)
