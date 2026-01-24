"""
Management command to seed initial FieldDefinitions
Usage: python manage.py seed_field_definitions
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models import FieldGroup, FieldDefinition


class Command(BaseCommand):
    help = "Seeds initial FieldDefinitions and FieldGroups"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n🌱 Seeding Field Definitions...\n"))

        # Create Field Groups
        groups = {
            "plot": FieldGroup.objects.get_or_create(
                name="plot",
                defaults={
                    "display_name": "Plot Elements",
                    "description": "Story structure, themes, and narrative elements",
                    "icon": "bi-book",
                    "color": "#007bff",
                    "order": 1,
                },
            )[0],
            "characters": FieldGroup.objects.get_or_create(
                name="characters",
                defaults={
                    "display_name": "Character Details",
                    "description": "Character development and relationships",
                    "icon": "bi-people",
                    "color": "#28a745",
                    "order": 2,
                },
            )[0],
            "world": FieldGroup.objects.get_or_create(
                name="world",
                defaults={
                    "display_name": "World Building",
                    "description": "Setting, atmosphere, and world details",
                    "icon": "bi-globe",
                    "color": "#17a2b8",
                    "order": 3,
                },
            )[0],
            "writing": FieldGroup.objects.get_or_create(
                name="writing",
                defaults={
                    "display_name": "Writing Style",
                    "description": "Tone, voice, and stylistic choices",
                    "icon": "bi-pen",
                    "color": "#ffc107",
                    "order": 4,
                },
            )[0],
        }

        self.stdout.write(f"✅ Created {len(groups)} Field Groups")

        # Create Field Definitions
        fields = [
            # PLOT ELEMENTS
            {
                "name": "story_themes",
                "display_name": "Story Themes",
                "description": "Main themes and messages of the story",
                "field_type": "textarea",
                "target_model": "project",
                "group": groups["plot"],
                "placeholder": "e.g., Love vs. Duty, Redemption, Coming of Age",
                "help_text": "What deeper meanings or messages does your story explore?",
                "is_ai_enrichable": True,
                "ai_prompt_template": "Based on the project outline:\n{{project_outline}}\n\nWhat are the main themes and deeper meanings in this story?",
                "order": 1,
            },
            {
                "name": "unique_selling_points",
                "display_name": "Unique Selling Points",
                "description": "What makes this story unique and compelling",
                "field_type": "textarea",
                "target_model": "project",
                "group": groups["plot"],
                "placeholder": "e.g., Unreliable narrator, Non-linear timeline",
                "help_text": "What sets this story apart from similar works?",
                "is_ai_enrichable": True,
                "ai_prompt_template": "Analyze this story outline:\n{{project_outline}}\n\nWhat are the unique selling points and distinctive elements?",
                "order": 2,
            },
            {
                "name": "plot_twists",
                "display_name": "Plot Twists & Surprises",
                "description": "Major plot twists and unexpected developments",
                "field_type": "json",
                "target_model": "project",
                "group": groups["plot"],
                "help_text": "Structure: [{chapter: 5, twist: 'description', impact: 'high'}]",
                "is_ai_enrichable": True,
                "order": 3,
            },
            # WORLD BUILDING
            {
                "name": "atmosphere_tone",
                "display_name": "Atmosphere & Tone",
                "description": "Overall mood and atmosphere of the story",
                "field_type": "textarea",
                "target_model": "project",
                "group": groups["world"],
                "placeholder": "e.g., Dark and mysterious with gothic undertones",
                "help_text": "What feeling should readers experience?",
                "is_ai_enrichable": True,
                "ai_prompt_template": "Based on the story:\n{{project_outline}}\n\nDescribe the atmosphere and tone that would best suit this narrative.",
                "order": 10,
            },
            {
                "name": "setting_details",
                "display_name": "Setting Details",
                "description": "Detailed description of the story's setting",
                "field_type": "markdown",
                "target_model": "project",
                "group": groups["world"],
                "help_text": "Time period, location, cultural context, etc.",
                "is_ai_enrichable": True,
                "order": 11,
            },
            {
                "name": "magic_system",
                "display_name": "Magic/Tech System",
                "description": "Rules and mechanics of magic or technology",
                "field_type": "markdown",
                "target_model": "project",
                "group": groups["world"],
                "help_text": "For fantasy/sci-fi: How does the supernatural/tech work?",
                "is_ai_enrichable": True,
                "order": 12,
            },
            # CHARACTER DETAILS
            {
                "name": "character_relationships",
                "display_name": "Character Relationships",
                "description": "Web of relationships between characters",
                "field_type": "json",
                "target_model": "project",
                "group": groups["characters"],
                "help_text": "Structure: [{from: 'Alice', to: 'Bob', type: 'romantic', notes: '...'}]",
                "is_ai_enrichable": True,
                "order": 20,
            },
            {
                "name": "character_arcs",
                "display_name": "Character Arcs",
                "description": "How characters change throughout the story",
                "field_type": "json",
                "target_model": "project",
                "group": groups["characters"],
                "help_text": "Structure: [{character: 'Alice', arc: 'victim to hero', stages: [...]}]",
                "is_ai_enrichable": True,
                "order": 21,
            },
            # WRITING STYLE
            {
                "name": "writing_style_notes",
                "display_name": "Writing Style Notes",
                "description": "Specific stylistic choices and guidelines",
                "field_type": "textarea",
                "target_model": "project",
                "group": groups["writing"],
                "placeholder": "e.g., Use short sentences for action, lyrical for introspection",
                "help_text": "Guidelines for maintaining consistent voice",
                "is_ai_enrichable": True,
                "order": 30,
            },
            {
                "name": "target_audience_details",
                "display_name": "Target Audience Details",
                "description": "Detailed profile of intended readers",
                "field_type": "textarea",
                "target_model": "project",
                "group": groups["writing"],
                "placeholder": "e.g., Young adults 16-25 who enjoy psychological thrillers",
                "help_text": "Who is this story written for?",
                "is_ai_enrichable": True,
                "ai_prompt_template": "Analyze this story:\n{{project_outline}}\n\nWho would be the ideal target audience? Provide a detailed profile.",
                "order": 31,
            },
            {
                "name": "content_warnings",
                "display_name": "Content Warnings",
                "description": "Sensitive topics that readers should be aware of",
                "field_type": "text",
                "target_model": "project",
                "group": groups["writing"],
                "placeholder": "e.g., Violence, Mental Health, Substance Abuse",
                "help_text": "Comma-separated list of content warnings",
                "is_ai_enrichable": False,
                "order": 32,
            },
        ]

        created_count = 0
        updated_count = 0

        for field_data in fields:
            field, created = FieldDefinition.objects.get_or_create(
                name=field_data["name"], defaults=field_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Created: {field.display_name}")
                )
            else:
                # Update existing field
                for key, value in field_data.items():
                    if key != "name":  # Don't update the name
                        setattr(field, key, value)
                field.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  Updated: {field.display_name}")
                )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ DONE! Created: {created_count}, Updated: {updated_count}\n"
            )
        )
        self.stdout.write(
            "You can now use these fields in the Field Management UI or via AI enrichment.\n"
        )
