"""
Management Command: Create Prompt Preset
=========================================

Creates predefined prompt system configurations for projects.

Usage:
    python manage.py create_prompt_preset --project-id 3 --preset kazakh_fairytale
    python manage.py create_prompt_preset --project-id 3 --preset fantasy_epic
"""

import logging
from django.core.management.base import BaseCommand, CommandError

from apps.writing_hub.handlers.prompt_builder_handler import PromptPresetFactory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Creates a prompt system preset for a project'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            required=True,
            help='ID of the project to configure'
        )
        parser.add_argument(
            '--preset',
            type=str,
            required=True,
            choices=['kazakh_fairytale', 'fantasy_epic', 'scifi', 'romance'],
            help='Preset template to use'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing configuration'
        )
    
    def handle(self, *args, **options):
        project_id = options['project_id']
        preset = options['preset']
        
        self.stdout.write(f"Creating preset '{preset}' for project {project_id}...")
        
        try:
            if preset == 'kazakh_fairytale':
                result = PromptPresetFactory.create_kazakh_fairytale_preset(project_id)
            else:
                raise CommandError(f"Preset '{preset}' not yet implemented")
            
            # Report results
            self.stdout.write(self.style.SUCCESS(f"\n✅ Preset '{preset}' created successfully!"))
            self.stdout.write(f"\nCreated components:")
            self.stdout.write(f"  - Master Style: {result['master_style'].name}")
            self.stdout.write(f"  - Characters: {len(result['characters'])}")
            for char in result['characters']:
                self.stdout.write(f"      • {char.name} ({char.get_role_display()})")
            self.stdout.write(f"  - Locations: {len(result['locations'])}")
            for loc in result['locations']:
                self.stdout.write(f"      • {loc.name}")
            self.stdout.write(f"  - Cultural Elements: {len(result['elements'])}")
            self.stdout.write(f"  - Scene Templates: {len(result['templates'])}")
            
            self.stdout.write(self.style.SUCCESS(
                f"\n🎨 Project ready for image generation with '{preset}' style!"
            ))
            
        except Exception as e:
            raise CommandError(f"Error creating preset: {e}")
