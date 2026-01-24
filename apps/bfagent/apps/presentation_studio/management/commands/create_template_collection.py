"""
Management command to create a template collection from a PPTX file
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files import File
from apps.presentation_studio.models import TemplateCollection
from apps.presentation_studio.services.template_analyzer import TemplateAnalyzer
import os


class Command(BaseCommand):
    help = 'Create a template collection from a master PPTX file'

    def add_arguments(self, parser):
        parser.add_argument(
            'pptx_path',
            type=str,
            help='Path to master PPTX file'
        )
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Name for the template collection'
        )
        parser.add_argument(
            '--client',
            type=str,
            default='',
            help='Client/Company name'
        )
        parser.add_argument(
            '--project',
            type=str,
            default='',
            help='Project name'
        )
        parser.add_argument(
            '--industry',
            type=str,
            choices=['tech', 'healthcare', 'finance', 'education', 'consulting', 'legal', 'retail', 'manufacturing', 'other'],
            default='other',
            help='Industry/sector'
        )
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Description of the template collection'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username of creator (default: admin)'
        )
        parser.add_argument(
            '--default',
            action='store_true',
            help='Set as default template collection'
        )
        parser.add_argument(
            '--system',
            action='store_true',
            help='Mark as system template (cannot be deleted)'
        )

    def handle(self, *args, **options):
        pptx_path = options['pptx_path']
        
        # Validate file exists
        if not os.path.exists(pptx_path):
            self.stdout.write(self.style.ERROR(f'File not found: {pptx_path}'))
            return
        
        # Get user
        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {options["username"]}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Analyzing PPTX: {pptx_path}'))
        
        # Analyze templates
        analyzer = TemplateAnalyzer()
        templates = analyzer.analyze_presentation(pptx_path)
        
        if not templates:
            self.stdout.write(self.style.ERROR('No templates found in PPTX'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(templates)} template types:'))
        for template_type in templates.keys():
            self.stdout.write(f'  - {template_type}')
        
        # Validate templates
        if not analyzer.validate_templates(templates):
            self.stdout.write(self.style.ERROR('Template validation failed'))
            return
        
        # If setting as default, unset other defaults
        if options['default']:
            TemplateCollection.objects.filter(is_default=True).update(is_default=False)
            self.stdout.write(self.style.WARNING('Unset previous default collections'))
        
        # Create collection
        try:
            with open(pptx_path, 'rb') as f:
                collection = TemplateCollection.objects.create(
                    name=options['name'],
                    description=options['description'],
                    client=options['client'],
                    project=options['project'],
                    industry=options['industry'],
                    templates=templates,
                    created_by=user,
                    is_default=options['default'],
                    is_system=options['system']
                )
                
                # Save PPTX file
                collection.master_pptx.save(
                    os.path.basename(pptx_path),
                    File(f),
                    save=True
                )
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Created template collection: {collection}'))
            self.stdout.write(f'  ID: {collection.id}')
            self.stdout.write(f'  Templates: {collection.template_count}')
            self.stdout.write(f'  Master PPTX: {collection.master_pptx.path}')
            
            if options['default']:
                self.stdout.write(self.style.SUCCESS('  ✓ Set as default'))
            if options['system']:
                self.stdout.write(self.style.SUCCESS('  ✓ Marked as system template'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating collection: {e}'))
            raise
