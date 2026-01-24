"""
Management command to setup Phase-Agent configurations with real relations
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import WorkflowPhase, Agents, PhaseAgentConfig


class Command(BaseCommand):
    help = "Setup Phase-Agent configurations for workflow system"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🤖 Setting up Phase-Agent configurations..."))
        self.stdout.write("")

        with transaction.atomic():
            # Get all phases
            phases = {
                phase.name: phase
                for phase in WorkflowPhase.objects.filter(is_active=True)
            }

            # Get all agents
            agents = {
                agent.agent_type: agent
                for agent in Agents.objects.filter(status="active")
            }

            self.stdout.write(f"📊 Found {len(phases)} phases and {len(agents)} active agents")
            self.stdout.write("")

            # Define Phase-Agent mappings
            phase_agent_mapping = {
                "Planning": [
                    {"agent_type": "prompt_agent", "required": True, "order": 1},
                ],
                "Outlining": [
                    {"agent_type": "prompt_agent", "required": False, "order": 1},
                ],
                "Character Development": [
                    {"agent_type": "character_agent", "required": True, "order": 1},
                ],
                "Writing": [
                    {"agent_type": "chapter_agent", "required": True, "order": 1},
                    {"agent_type": "writer_agent", "required": False, "order": 2},
                ],
                "Revision": [
                    {"agent_type": "consistency_agent", "required": True, "order": 1},
                ],
            }

            config_count = 0
            for phase_name, agent_configs in phase_agent_mapping.items():
                phase = phases.get(phase_name)
                if not phase:
                    self.stdout.write(self.style.WARNING(f"  ⚠️  Phase '{phase_name}' not found"))
                    continue

                self.stdout.write(f"\n📋 {phase_name}:")

                for config in agent_configs:
                    agent_type = config["agent_type"]
                    agent = agents.get(agent_type)

                    if not agent:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠️  Agent type '{agent_type}' not found")
                        )
                        continue

                    # Create or update PhaseAgentConfig
                    pac, created = PhaseAgentConfig.objects.get_or_create(
                        phase=phase,
                        agent=agent,
                        defaults={
                            "is_required": config["required"],
                            "order": config["order"],
                            "description": f"{agent.name} for {phase_name} phase",
                        },
                    )

                    if created:
                        config_count += 1
                        status = "✅ Created"
                    else:
                        status = "ℹ️  Exists"

                    self.stdout.write(
                        f"  {status}: {agent.name} ({agent.agent_type})"
                        + (f" [Required]" if config["required"] else "")
                    )

            # Summary
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"📊 Summary: Created {config_count} new configurations"))
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("🎉 Phase-Agent setup complete!"))
