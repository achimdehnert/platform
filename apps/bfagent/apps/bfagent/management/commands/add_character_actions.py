"""
Management command to add Character Profile and Relationship actions
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import AgentAction, Agents


class Command(BaseCommand):
    help = "Add Character Profile and Relationship actions to Character Agent"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n🎭 Adding Character Actions...\n"))

        with transaction.atomic():
            # Get or create Character Agent
            character_agent, created = Agents.objects.get_or_create(
                agent_type="character_agent",
                defaults={
                    "name": "Character Development Agent",
                    "description": "AI agent specialized in character development and relationships",
                    "status": "active",
                    "system_prompt": "You are an expert character development AI specialized in creating deep, compelling characters.",
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS("✅ Created Character Agent"))
            else:
                self.stdout.write("   Character Agent already exists")

            # Actions to add
            actions_data = [
                {
                    "name": "develop_character_profile",
                    "display_name": "Develop Character Profile",
                    "description": "Create detailed character profile with backstory, personality, and traits",
                    "target_model": "character",
                    "target_fields": ["background", "personality", "motivation", "conflict"],
                },
                {
                    "name": "analyze_character_arc",
                    "display_name": "Analyze Character Arc",
                    "description": "Analyze and develop character growth arc throughout the story",
                    "target_model": "character",
                    "target_fields": ["arc"],
                },
                {
                    "name": "create_character_relationships",
                    "display_name": "Create Character Relationships",
                    "description": "Define relationships between characters including conflicts and bonds",
                    "target_model": "character",
                    "target_fields": ["description"],
                },
                {
                    "name": "enhance_character_voice",
                    "display_name": "Enhance Character Voice",
                    "description": "Develop unique dialogue style and voice for character",
                    "target_model": "character",
                    "target_fields": ["personality"],
                },
                {
                    "name": "generate_character_backstory",
                    "display_name": "Generate Character Backstory",
                    "description": "Create detailed backstory and history for character",
                    "target_model": "character",
                    "target_fields": ["background"],
                },
            ]

            created_count = 0
            for action_data in actions_data:
                action, created = AgentAction.objects.get_or_create(
                    agent=character_agent,
                    name=action_data["name"],
                    defaults={
                        "display_name": action_data["display_name"],
                        "description": action_data["description"],
                        "target_model": action_data["target_model"],
                        "target_fields": action_data["target_fields"],
                        "is_active": True,
                    },
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Created: {action_data['display_name']}")
                    )
                    created_count += 1
                else:
                    self.stdout.write(f"   Skipped: {action_data['display_name']} (exists)")

            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 Added {created_count} new Character Actions!\n")
            )
