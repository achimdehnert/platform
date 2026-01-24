"""
Management command to setup AgentActions with proper DB relations
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import Agents, AgentAction, WorkflowPhase, PhaseActionConfig


class Command(BaseCommand):
    help = "Setup AgentActions for all agents"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🎯 Setting up Agent Actions..."))
        self.stdout.write("")

        with transaction.atomic():
            # Define actions for each agent type
            agent_actions_map = {
                "prompt_agent": [
                    {
                        "name": "generate_prompt_template",
                        "display_name": "Generate Prompt Template",
                        "description": "Create a new prompt template based on requirements",
                        "order": 1,
                    },
                    {
                        "name": "optimize_existing_template",
                        "display_name": "Optimize Existing Template",
                        "description": "Improve an existing prompt template",
                        "order": 2,
                    },
                    {
                        "name": "analyze_template_quality",
                        "display_name": "Analyze Template Quality",
                        "description": "Evaluate the quality of a prompt template",
                        "order": 3,
                    },
                    {
                        "name": "generate_template_variations",
                        "display_name": "Generate Template Variations",
                        "description": "Create multiple variations of a template",
                        "order": 4,
                    },
                ],
                "character_agent": [
                    {
                        "name": "generate_character_cast",
                        "display_name": "Generate Character Cast",
                        "description": "Create a complete cast of characters",
                        "order": 1,
                    },
                    {
                        "name": "derive_characters_from_outline",
                        "display_name": "Derive Characters from Outline",
                        "description": "Extract and develop characters from story outline",
                        "order": 2,
                    },
                    {
                        "name": "develop_character_backstory",
                        "display_name": "Develop Character Backstory",
                        "description": "Create detailed backstory for a character",
                        "order": 3,
                    },
                    {
                        "name": "analyze_character_arc",
                        "display_name": "Analyze Character Arc",
                        "description": "Review and improve character development arc",
                        "order": 4,
                    },
                ],
                "chapter_agent": [
                    {
                        "name": "generate_outline",
                        "display_name": "Generate Chapter Outline",
                        "description": "Create a detailed outline for a chapter",
                        "order": 1,
                    },
                    {
                        "name": "write_draft",
                        "display_name": "Write Chapter Draft",
                        "description": "Generate a complete chapter draft",
                        "order": 2,
                    },
                    {
                        "name": "expand_scene",
                        "display_name": "Expand Scene",
                        "description": "Expand a scene with more details",
                        "order": 3,
                    },
                    {
                        "name": "summarize",
                        "display_name": "Summarize Chapter",
                        "description": "Create a concise summary of the chapter",
                        "order": 4,
                    },
                    {
                        "name": "improve_prose",
                        "display_name": "Improve Prose",
                        "description": "Enhance writing quality and style",
                        "order": 5,
                    },
                    {
                        "name": "add_dialogue",
                        "display_name": "Add Dialogue",
                        "description": "Generate dialogue for scenes",
                        "order": 6,
                    },
                ],
                "story_agent": [
                    {
                        "name": "generate_plot_points",
                        "display_name": "Generate Plot Points",
                        "description": "Create key plot points for the story",
                        "order": 1,
                    },
                    {
                        "name": "analyze_pacing",
                        "display_name": "Analyze Pacing",
                        "description": "Review story pacing and rhythm",
                        "order": 2,
                    },
                    {
                        "name": "check_arc_consistency",
                        "display_name": "Check Arc Consistency",
                        "description": "Verify story arc consistency",
                        "order": 3,
                    },
                    {
                        "name": "suggest_arc_improvements",
                        "display_name": "Suggest Arc Improvements",
                        "description": "Recommend improvements to story arcs",
                        "order": 4,
                    },
                    {
                        "name": "identify_plot_holes",
                        "display_name": "Identify Plot Holes",
                        "description": "Find and suggest fixes for plot holes",
                        "order": 5,
                    },
                ],
                "consistency_agent": [
                    {
                        "name": "check_consistency",
                        "display_name": "Check Consistency",
                        "description": "Perform comprehensive consistency check",
                        "order": 1,
                    },
                    {
                        "name": "check_character_voice",
                        "display_name": "Check Character Voice",
                        "description": "Verify character voice consistency",
                        "order": 2,
                    },
                    {
                        "name": "check_timeline",
                        "display_name": "Check Timeline",
                        "description": "Verify timeline consistency",
                        "order": 3,
                    },
                    {
                        "name": "check_setting",
                        "display_name": "Check Setting",
                        "description": "Verify setting consistency",
                        "order": 4,
                    },
                    {
                        "name": "calculate_score",
                        "display_name": "Calculate Consistency Score",
                        "description": "Generate overall consistency score",
                        "order": 5,
                    },
                ],
                "writer_agent": [
                    {
                        "name": "expand_scene",
                        "display_name": "Expand Scene",
                        "description": "Add depth and detail to scenes",
                        "order": 1,
                    },
                    {
                        "name": "enhance_description",
                        "display_name": "Enhance Description",
                        "description": "Improve descriptive passages",
                        "order": 2,
                    },
                    {
                        "name": "improve_flow",
                        "display_name": "Improve Flow",
                        "description": "Enhance narrative flow",
                        "order": 3,
                    },
                ],
            }

            created_count = 0
            updated_count = 0

            # Get all active agents
            agents = {agent.agent_type: agent for agent in Agents.objects.filter(status="active")}

            self.stdout.write(f"📊 Found {len(agents)} active agents")
            self.stdout.write("")

            for agent_type, actions_config in agent_actions_map.items():
                agent = agents.get(agent_type)
                if not agent:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠️  Agent type '{agent_type}' not found - skipping")
                    )
                    continue

                self.stdout.write(f"\n🤖 {agent.name} ({agent_type}):")

                for action_config in actions_config:
                    action, created = AgentAction.objects.get_or_create(
                        agent=agent,
                        name=action_config["name"],
                        defaults={
                            "display_name": action_config["display_name"],
                            "description": action_config["description"],
                            "order": action_config["order"],
                            "is_active": True,
                        },
                    )

                    if created:
                        created_count += 1
                        status = "✅ Created"
                    else:
                        # Update if exists
                        action.display_name = action_config["display_name"]
                        action.description = action_config["description"]
                        action.order = action_config["order"]
                        action.save()
                        updated_count += 1
                        status = "🔄 Updated"

                    self.stdout.write(f"  {status}: {action.display_name}")

            # Summary
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"📊 Summary: Created {created_count} actions, updated {updated_count} actions"
                )
            )
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("🎉 Agent actions setup complete!"))
