"""
Django Management Command: Check Workflow Consistency
Usage: python manage.py check_workflow
"""

from django.core.management.base import BaseCommand

from apps.bfagent.models import AgentAction, PhaseActionConfig, WorkflowPhase


class Command(BaseCommand):
    help = "Check workflow consistency: Phases → Actions → Templates → Agents"

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🔍 WORKFLOW CONSISTENCY CHECK"))
        self.stdout.write("=" * 80)

        # 1. CHECK: Alle Phasen
        phases = WorkflowPhase.objects.all().order_by("name")
        self.stdout.write(f"\n📊 Found {phases.count()} Workflow Phases:")
        for phase in phases:
            self.stdout.write(f"  - {phase.name}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🎯 PHASE → ACTION → TEMPLATE → AGENT CHECK"))
        self.stdout.write("=" * 80)

        issues = []
        recommendations = []

        for phase in phases:
            self.stdout.write(f"\n{'=' * 80}")
            self.stdout.write(self.style.WARNING(f"📌 PHASE: {phase.name}"))
            self.stdout.write("=" * 80)

            # Check Phase Actions
            phase_configs = PhaseActionConfig.objects.filter(phase=phase).select_related(
                "action__agent", "action__prompt_template"
            )

            if not phase_configs.exists():
                issue = f"Phase '{phase.name}' has NO actions configured!"
                self.stdout.write(self.style.ERROR(f"  ❌ {issue}"))
                issues.append(issue)
                recommendations.append(f"Create PhaseActionConfig for phase: {phase.name}")
                continue

            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Found {phase_configs.count()} action(s) for this phase")
            )

            for i, config in enumerate(phase_configs, 1):
                action = config.action
                self.stdout.write(f"\n  {i}. ACTION: {action.display_name} (order: {config.order})")
                self.stdout.write(f"     Internal Name: {action.name}")

                required_text = (
                    self.style.SUCCESS("✅ YES")
                    if config.is_required
                    else self.style.WARNING("⚠️  NO")
                )
                self.stdout.write(f"     Required: {required_text}")

                # Check Agent
                if action.agent:
                    self.stdout.write(self.style.SUCCESS(f"     Agent: ✅ {action.agent.name}"))
                else:
                    issue = f"Action '{action.display_name}' has NO agent assigned!"
                    self.stdout.write(self.style.ERROR(f"     Agent: ❌ {issue}"))
                    issues.append(issue)
                    recommendations.append(f"Assign an agent to action: {action.display_name}")

                # Check Template
                if action.prompt_template:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"     Template: ✅ {action.prompt_template.name} (v{action.prompt_template.version})"
                        )
                    )
                else:
                    warning = f"Action '{action.display_name}' has NO prompt template!"
                    self.stdout.write(self.style.WARNING(f"     Template: ⚠️  {warning}"))
                    issues.append(warning)
                    recommendations.append(
                        f"Create PromptTemplate for action: {action.display_name}"
                    )

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 SUMMARY"))
        self.stdout.write("=" * 80)

        # Count stats
        total_phases = phases.count()
        phases_with_actions = PhaseActionConfig.objects.values("phase").distinct().count()
        total_actions = AgentAction.objects.count()
        actions_with_templates = AgentAction.objects.filter(prompt_template__isnull=False).count()
        actions_with_agents = AgentAction.objects.filter(agent__isnull=False).count()

        self.stdout.write(f"\n📈 Statistics:")
        self.stdout.write(f"  Total Phases: {total_phases}")
        self.stdout.write(f"  Phases with Actions: {phases_with_actions}/{total_phases}")
        self.stdout.write(f"  Total Actions: {total_actions}")
        self.stdout.write(f"  Actions with Agents: {actions_with_agents}/{total_actions}")
        self.stdout.write(f"  Actions with Templates: {actions_with_templates}/{total_actions}")

        self.stdout.write(f"\n🔍 Issues Found: {len(issues)}")
        if issues:
            self.stdout.write(self.style.ERROR("\n❌ ISSUES:"))
            for issue in issues:
                self.stdout.write(f"  - {issue}")
        else:
            self.stdout.write(self.style.SUCCESS("  ✅ No critical issues found!"))

        self.stdout.write(f"\n💡 RECOMMENDATIONS ({len(recommendations)}):")
        if recommendations:
            for rec in recommendations:
                self.stdout.write(self.style.WARNING(f"  → {rec}"))
        else:
            self.stdout.write(self.style.SUCCESS("  ✅ Everything looks good!"))

        # Detailed Action Report
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📋 DETAILED ACTION REPORT"))
        self.stdout.write("=" * 80)

        all_actions = (
            AgentAction.objects.all()
            .select_related("agent", "prompt_template")
            .order_by("agent__name", "order")
        )

        for action in all_actions:
            self.stdout.write(f"\n{action.display_name}")

            if action.agent:
                self.stdout.write(self.style.SUCCESS(f"  Agent: ✅ {action.agent.name}"))
            else:
                self.stdout.write(self.style.ERROR(f"  Agent: ❌ NONE"))

            if action.prompt_template:
                self.stdout.write(
                    self.style.SUCCESS(f"  Template: ✅ {action.prompt_template.name}")
                )
            else:
                self.stdout.write(self.style.WARNING(f"  Template: ⚠️  NONE"))

            if action.is_active:
                self.stdout.write(self.style.SUCCESS(f"  Active: ✅"))
            else:
                self.stdout.write(self.style.WARNING(f"  Active: ⚠️  NO"))

            phase_count = PhaseActionConfig.objects.filter(action=action).count()
            self.stdout.write(f"  Used in Phases: {phase_count}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ CHECK COMPLETE"))
        self.stdout.write("=" * 80)
