"""
Initialize Workflow Phases and Agent Actions
Ensures consistency between BookType-Phases and Phase-Actions
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Setup Django environment - use development settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

# Import models AFTER django.setup()
from apps.bfagent.models import AgentAction, Agents, PhaseActionConfig, WorkflowPhase


def init_workflow_phases():
    """Create standard workflow phases"""
    phases = [
        {
            "name": "outline",
            "description": "Structure and plot development",
            "icon": "diagram-3",
            "color": "primary",
        },
        {
            "name": "writing main",
            "description": "Main writing phase",
            "icon": "pencil",
            "color": "success",
        },
        {
            "name": "Planning",
            "description": "Initial planning and brainstorming",
            "icon": "lightbulb",
            "color": "warning",
        },
        {
            "name": "Outlining",
            "description": "Creating detailed outline",
            "icon": "list-ol",
            "color": "info",
        },
        {
            "name": "Character Development",
            "description": "Developing characters and backstories",
            "icon": "people",
            "color": "purple",
        },
        {
            "name": "World Building",
            "description": "Creating the story world",
            "icon": "globe",
            "color": "teal",
        },
        {
            "name": "Writing Chapters",
            "description": "Writing individual chapters",
            "icon": "file-text",
            "color": "success",
        },
        {
            "name": "Editing",
            "description": "Editing and revising content",
            "icon": "pen",
            "color": "orange",
        },
        {
            "name": "Review",
            "description": "Final review and quality check",
            "icon": "eye",
            "color": "info",
        },
        {
            "name": "Finalization",
            "description": "Final touches and preparation",
            "icon": "check-circle",
            "color": "success",
        },
        {
            "name": "Publishing",
            "description": "Publishing and distribution",
            "icon": "box-arrow-up",
            "color": "primary",
        },
    ]

    created = 0
    updated = 0

    for phase_data in phases:
        phase, was_created = WorkflowPhase.objects.get_or_create(
            name=phase_data["name"],
            defaults={
                "description": phase_data["description"],
                "icon": phase_data["icon"],
                "color": phase_data["color"],
                "is_active": True,
            },
        )

        if was_created:
            created += 1
            print(f"✅ Created phase: {phase.name}")
        else:
            # Update existing
            phase.description = phase_data["description"]
            phase.icon = phase_data["icon"]
            phase.color = phase_data["color"]
            phase.save()
            updated += 1
            print(f"🔄 Updated phase: {phase.name}")

    print(f"\n📊 Summary: {created} created, {updated} updated")
    return WorkflowPhase.objects.all().count()


def init_agent_actions():
    """Create essential agent actions"""

    # Get or create Content Writing Agent
    agent, _ = Agents.objects.get_or_create(
        agent_type="content_writing_agent",
        defaults={
            "name": "Content Writing Agent",
            "description": "Generates complete written content",
            "status": "active",
        },
    )

    actions = [
        {
            "name": "outline",
            "display_name": "Create Outline",
            "description": "Create a concise story outline with 3-5 chapters",
            "agent": agent,
        },
        {
            "name": "write_short_content",
            "display_name": "Write Short Content",
            "description": "Write a complete short story (1500-2500 words)",
            "agent": agent,
        },
        {
            "name": "write_everything",
            "display_name": "Write Everything",
            "description": "Write complete work based on outline (3-8 chapters)",
            "agent": agent,
        },
    ]

    created = 0
    updated = 0

    for action_data in actions:
        action, was_created = AgentAction.objects.get_or_create(
            name=action_data["name"],
            agent=action_data["agent"],
            defaults={
                "display_name": action_data["display_name"],
                "description": action_data["description"],
                "is_active": True,
                "order": 0,
            },
        )

        if was_created:
            created += 1
            print(f"✅ Created action: {action.display_name} ({action.name})")
        else:
            action.display_name = action_data["display_name"]
            action.description = action_data["description"]
            action.is_active = True
            action.save()
            updated += 1
            print(f"🔄 Updated action: {action.display_name}")

    print(f"\n📊 Summary: {created} created, {updated} updated")
    return AgentAction.objects.filter(agent=agent).count()


def verify_consistency():
    """Verify that phases and actions are consistent"""
    print("\n" + "=" * 80)
    print("🔍 CONSISTENCY CHECK")
    print("=" * 80)

    # Check workflow phases
    phases = WorkflowPhase.objects.all()
    print(f"\n📋 Workflow Phases: {phases.count()}")
    for phase in phases:
        action_count = PhaseActionConfig.objects.filter(phase=phase).count()
        print(f"   {phase.name}: {action_count} actions")

    # Check agent actions
    actions = AgentAction.objects.filter(is_active=True)
    print(f"\n⚡ Active Agent Actions: {actions.count()}")
    for action in actions:
        phase_count = PhaseActionConfig.objects.filter(action=action).count()
        print(f"   {action.display_name} ({action.agent.name}): used in {phase_count} phases")

    # Check orphaned configs
    orphaned = PhaseActionConfig.objects.filter(action__is_active=False).count()
    if orphaned > 0:
        print(f"\n⚠️  Warning: {orphaned} phase-action configs reference inactive actions")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("🚀 Initializing Workflow Phases and Agent Actions\n")

    print("=" * 80)
    print("STEP 1: Workflow Phases")
    print("=" * 80)
    total_phases = init_workflow_phases()

    print("\n" + "=" * 80)
    print("STEP 2: Agent Actions")
    print("=" * 80)
    total_actions = init_agent_actions()

    verify_consistency()

    print("\n✅ Initialization complete!")
    print(f"   Total Workflow Phases: {total_phases}")
    print(f"   Total Active Actions: {AgentAction.objects.filter(is_active=True).count()}")
