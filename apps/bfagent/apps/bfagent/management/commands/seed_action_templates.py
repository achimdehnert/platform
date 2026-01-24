"""
Seed ActionTemplate mappings with sensible defaults
Creates initial Action → Template associations for common workflows
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import AgentAction, PromptTemplate, ActionTemplate


class Command(BaseCommand):
    help = "Seed ActionTemplate mappings with intelligent defaults"

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing ActionTemplates before seeding',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("🌱 Seeding ActionTemplate Mappings"))
        self.stdout.write("=" * 60 + "\n")

        if options['reset']:
            self.stdout.write(self.style.WARNING("🗑️  Deleting existing ActionTemplates..."))
            deleted_count = ActionTemplate.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"   Deleted {deleted_count} mappings\n"))

        # Define sensible Action → Template mappings
        mappings = [
            # OUTLINE GENERATION
            {
                'action_name': 'generate_outline',
                'templates': [
                    {'name': 'Three-Act Structure', 'is_default': True, 'order': 1},
                    {'name': 'Hero\'s Journey', 'is_default': False, 'order': 2},
                    {'name': 'Save the Cat', 'is_default': False, 'order': 3},
                ]
            },
            # CHARACTER DEVELOPMENT
            {
                'action_name': 'generate_character_cast',
                'templates': [
                    {'name': 'Character Profile Deep', 'is_default': True, 'order': 1},
                    {'name': 'Character Quick Sketch', 'is_default': False, 'order': 2},
                ]
            },
            {
                'action_name': 'enhance_character',
                'templates': [
                    {'name': 'Character Arc Builder', 'is_default': True, 'order': 1},
                    {'name': 'Dialogue Voice Generator', 'is_default': False, 'order': 2},
                ]
            },
            # WORLD BUILDING
            {
                'action_name': 'generate_world',
                'templates': [
                    {'name': 'World-Building Framework', 'is_default': True, 'order': 1},
                ]
            },
            # CHAPTER WRITING
            {
                'action_name': 'write_chapter_draft',
                'templates': [
                    {'name': 'Chapter Structure Template', 'is_default': True, 'order': 1},
                ]
            },
            {
                'action_name': 'summarize_chapter',
                'templates': [
                    {'name': 'Summary Template', 'is_default': True, 'order': 1},
                ]
            },
            # CONFLICT & STAKES
            {
                'action_name': 'enhance_conflict',
                'templates': [
                    {'name': 'Conflict Escalation', 'is_default': True, 'order': 1},
                ]
            },
        ]

        created_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic():
            for mapping in mappings:
                action_name = mapping['action_name']
                
                # Find the action
                try:
                    action = AgentAction.objects.get(name=action_name)
                except AgentAction.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  Action '{action_name}' not found - skipping")
                    )
                    skipped_count += 1
                    continue

                self.stdout.write(f"\n📋 Processing: {action.display_name}")

                for template_config in mapping['templates']:
                    template_name = template_config['name']
                    
                    # Find the template
                    try:
                        template = PromptTemplate.objects.get(name=template_name)
                    except PromptTemplate.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"   ⚠️  Template '{template_name}' not found")
                        )
                        skipped_count += 1
                        continue

                    # Check if mapping already exists
                    if ActionTemplate.objects.filter(
                        action=action,
                        template=template
                    ).exists():
                        self.stdout.write(
                            self.style.WARNING(f"   ⏭️  Mapping already exists: {template_name}")
                        )
                        skipped_count += 1
                        continue

                    # Create the mapping
                    try:
                        action_template = ActionTemplate.objects.create(
                            action=action,
                            template=template,
                            is_default=template_config['is_default'],
                            order=template_config['order'],
                            description_override=f"Recommended template for {action.display_name}"
                        )
                        
                        default_marker = " (DEFAULT)" if template_config['is_default'] else ""
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   ✅ Created: {template_name}{default_marker}"
                            )
                        )
                        created_count += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"   ❌ Error: {str(e)}")
                        )
                        error_count += 1

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 Seeding Summary:"))
        self.stdout.write(f"   ✅ Created: {created_count} mappings")
        if skipped_count > 0:
            self.stdout.write(f"   ⏭️  Skipped: {skipped_count} mappings")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"   ❌ Errors: {error_count} mappings"))
        self.stdout.write("=" * 60 + "\n")

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"🎉 Successfully seeded {created_count} ActionTemplate mappings!\n"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("⚠️  No new mappings created\n")
            )
