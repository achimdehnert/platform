"""
Simple PromptTemplate seeding - uses actual model fields
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import PromptTemplate, Agents


class Command(BaseCommand):
    help = "Seed basic PromptTemplates (simplified version)"

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing templates')

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("🌱 Seeding Simple PromptTemplates"))
        self.stdout.write("=" * 60 + "\n")

        # Get first agent (or create a default one)
        agent = Agents.objects.first()
        if not agent:
            self.stdout.write(self.style.ERROR("❌ No agents found! Please create agents first."))
            self.stdout.write("   Run: python manage.py setup_agent_actions")
            return

        if options['reset']:
            deleted = PromptTemplate.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"🗑️  Deleted {deleted} templates\n"))

        # Simple templates with ONLY the fields that exist in the model
        templates = [
            {
                'name': 'Three-Act Structure',
                'description': 'Classic three-act story structure',
                'template_text': '''Create a story outline using three-act structure:

ACT 1 - SETUP: Introduce world, characters, and inciting incident
ACT 2 - CONFRONTATION: Rising action, midpoint, darkest moment
ACT 3 - RESOLUTION: Climax and resolution

Project: {{ project.title }}
Genre: {{ project.genre }}''',
                'agent': agent,
            },
            {
                'name': 'Character Profile',
                'description': 'Comprehensive character development',
                'template_text': '''Create a detailed character profile:

BASICS: Name, age, occupation, appearance
PSYCHOLOGY: Personality, strengths, weaknesses, motivations
CHARACTER ARC: Starting point, transformation, ending point

Project: {{ project.title }}''',
                'agent': agent,
            },
            {
                'name': 'Chapter Structure',
                'description': 'Template for chapter writing',
                'template_text': '''Write a chapter with:

OPENING HOOK: Grab attention immediately
SCENE DEVELOPMENT: Clear goal, obstacles, emotional progression
PACING: Mix action and reflection
CLOSING: Mini-cliffhanger or transition

Chapter: {{ chapter.title }}
Word Count Target: {{ chapter.word_count }}''',
                'agent': agent,
            },
        ]

        created = 0
        with transaction.atomic():
            for tpl_data in templates:
                obj, was_created = PromptTemplate.objects.get_or_create(
                    name=tpl_data['name'],
                    agent=tpl_data['agent'],
                    defaults={
                        'description': tpl_data['description'],
                        'template_text': tpl_data['template_text'],
                        'version': 1,
                    }
                )
                if was_created:
                    self.stdout.write(self.style.SUCCESS(f"✅ Created: {tpl_data['name']}"))
                    created += 1
                else:
                    self.stdout.write(self.style.WARNING(f"⏭️  Exists: {tpl_data['name']}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"🎉 Seeded {created} new templates!"))
        self.stdout.write("=" * 60 + "\n")
