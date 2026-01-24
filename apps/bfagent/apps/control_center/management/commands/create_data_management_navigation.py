"""
Management command to create Data Management navigation section and items
"""
from django.core.management.base import BaseCommand
from apps.control_center.models_navigation import NavigationSection, NavigationItem


class Command(BaseCommand):
    help = 'Create Data Management navigation section with items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('\n📋 Creating Data Management Navigation\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be saved\n'))
        
        # Check if section already exists
        section_code = 'data_management'
        section = NavigationSection.objects.filter(code=section_code).first()
        
        if section:
            self.stdout.write(self.style.WARNING(f'⚠️  Section "{section_code}" already exists: {section.name}'))
        else:
            if not dry_run:
                section = NavigationSection.objects.create(
                    code=section_code,
                    name='Data Management',
                    description='Verwaltung von Stammdaten und Datenstrukturen',
                    icon='bi-database',
                    color='info',
                    order=30,
                    slug='data-management',
                    is_active=True,
                    is_collapsible=True,
                    is_collapsed_default=False,
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Created section: {section.name}'))
            else:
                self.stdout.write(f'[DRY RUN] Would create section: Data Management')
        
        if section or dry_run:
            # Define navigation items
            items = [
                {
                    'code': 'domain_arts',
                    'name': 'Domain Arts',
                    'description': 'Verwaltung der Domain-Arten',
                    'item_type': 'link',
                    'url_name': 'control_center:domain-arts-list',
                    'icon': 'bi-diagram-3',
                    'order': 10,
                },
                {
                    'code': 'domain_types',
                    'name': 'Domain Types',
                    'description': 'Verwaltung der Domain-Typen',
                    'item_type': 'link',
                    'url_name': 'control_center:domain-types-list',
                    'icon': 'bi-list-nested',
                    'order': 20,
                },
                {
                    'code': 'workflow_phases',
                    'name': 'Workflow Phasen',
                    'description': 'Verwaltung der Workflow-Phasen',
                    'item_type': 'link',
                    'url_name': 'bfagent:workflow-phases',
                    'icon': 'bi-arrow-right-circle',
                    'order': 30,
                },
                {
                    'code': 'agents',
                    'name': 'Agents',
                    'description': 'Verwaltung der KI-Agenten',
                    'item_type': 'link',
                    'url_name': 'bfagent:agents-list',
                    'icon': 'bi-cpu',
                    'order': 40,
                },
                {
                    'code': 'llm_models',
                    'name': 'LLM Modelle',
                    'description': 'Verwaltung der LLM-Modelle',
                    'item_type': 'link',
                    'url_name': 'bfagent:llms-list',
                    'icon': 'bi-lightning',
                    'order': 50,
                },
                {
                    'code': 'prompt_templates',
                    'name': 'Prompt Templates',
                    'description': 'Verwaltung der Prompt-Vorlagen',
                    'item_type': 'link',
                    'url_name': 'bfagent:prompt-templates',
                    'icon': 'bi-file-text',
                    'order': 60,
                },
                {
                    'code': 'field_groups',
                    'name': 'Field Groups',
                    'description': 'Verwaltung der Feldgruppen',
                    'item_type': 'link',
                    'url_name': 'bfagent:field-groups',
                    'icon': 'bi-collection',
                    'order': 70,
                },
            ]
            
            self.stdout.write(f'\n📊 Creating {len(items)} navigation items:')
            created_count = 0
            updated_count = 0
            
            for item_data in items:
                existing = None
                if not dry_run and section:
                    existing = NavigationItem.objects.filter(
                        section=section,
                        code=item_data['code']
                    ).first()
                
                if existing:
                    self.stdout.write(f'  ⏭️  Item "{item_data["name"]}" already exists')
                    updated_count += 1
                elif dry_run:
                    self.stdout.write(f'  [DRY RUN] Would create: {item_data["name"]}')
                else:
                    NavigationItem.objects.create(
                        section=section,
                        **item_data
                    )
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created: {item_data["name"]}'))
                    created_count += 1
            
            # Summary
            self.stdout.write('\n' + '='*60)
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\n🔍 DRY RUN COMPLETE:'))
                self.stdout.write(f'  Would create: 1 section, {len(items)} items')
            else:
                self.stdout.write(self.style.SUCCESS(f'\n✅ COMPLETE:'))
                self.stdout.write(f'  Created items: {created_count}')
                self.stdout.write(f'  Existing items: {updated_count}')
                self.stdout.write(f'\n💡 Access at: /hub/control-center/ (when domain exists)')
