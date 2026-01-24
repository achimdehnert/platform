"""
Management command to link WorkflowPhases with DomainTypes via DomainPhase

Phase 2 of Multi-Hub Framework Integration:
- Creates DomainPhase links between DomainTypes and WorkflowPhases
- Assigns appropriate phases for each book type
- Configures sort order and requirements
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.bfagent.models import WorkflowPhase
from apps.bfagent.models_domains import DomainArt, DomainType, DomainPhase


class Command(BaseCommand):
    help = 'Link WorkflowPhases with DomainTypes for Multi-Hub Framework'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing DomainPhase links before creating new ones',
        )
        parser.add_argument(
            '--domain',
            type=str,
            help='Only process specific domain art (e.g., book_creation)',
        )

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('🔗 Phase 2: Linking DomainPhases'))
        self.stdout.write('=' * 60 + '\n')

        # Clear existing links if requested
        if options['clear']:
            count = DomainPhase.objects.all().count()
            DomainPhase.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Cleared {count} existing DomainPhase links'))
            self.stdout.write('')

        # Phase mappings for book_creation domain
        book_writing_phases = [
            ('Planning', 10, True),
            ('Character Development', 20, True),
            ('World Building', 30, False),
            ('Outlining', 40, True),
            ('First Draft', 50, True),
            ('Revision', 60, True),
            ('Editing', 70, True),
            ('Proofreading', 80, False),
            ('Formatting', 90, False),
            ('Publishing', 100, False),
        ]

        # Type-specific phase configurations
        type_configs = {
            'fiction': {
                'phases': book_writing_phases,
                'description': 'Standard fiction writing workflow'
            },
            'non_fiction': {
                'phases': [
                    ('Planning', 10, True),
                    ('Research', 15, True),
                    ('Outlining', 30, True),
                    ('First Draft', 50, True),
                    ('Fact Checking', 55, True),
                    ('Revision', 60, True),
                    ('Editing', 70, True),
                    ('Proofreading', 80, False),
                    ('Formatting', 90, False),
                    ('Publishing', 100, False),
                ],
                'description': 'Non-fiction with research and fact-checking'
            },
            'technical': {
                'phases': [
                    ('Planning', 10, True),
                    ('Research', 15, True),
                    ('Technical Review', 25, True),
                    ('Outlining', 30, True),
                    ('First Draft', 50, True),
                    ('Code Examples', 55, False),
                    ('Technical Editing', 65, True),
                    ('Revision', 70, True),
                    ('Proofreading', 80, False),
                    ('Formatting', 90, False),
                ],
                'description': 'Technical writing with code examples'
            },
            'children': {
                'phases': [
                    ('Planning', 10, True),
                    ('Character Development', 20, True),
                    ('Illustration Planning', 25, False),
                    ('Outlining', 30, True),
                    ('First Draft', 50, True),
                    ('Age-Appropriate Review', 55, True),
                    ('Revision', 60, True),
                    ('Editing', 70, True),
                    ('Illustration', 75, False),
                    ('Formatting', 90, False),
                ],
                'description': "Children's books with illustration support"
            },
        }

        try:
            with transaction.atomic():
                # Get or filter domain
                if options['domain']:
                    domains = DomainArt.objects.filter(name=options['domain'])
                    if not domains.exists():
                        self.stdout.write(self.style.ERROR(f'❌ Domain "{options["domain"]}" not found'))
                        return
                else:
                    domains = DomainArt.objects.filter(is_active=True)

                total_links = 0
                
                for domain in domains:
                    self.stdout.write(self.style.HTTP_INFO(f'\n📦 Processing: {domain.display_name}'))
                    self.stdout.write('-' * 60)

                    # Get domain types
                    domain_types = domain.domain_types.filter(is_active=True)
                    
                    for domain_type in domain_types:
                        self.stdout.write(f'\n  📁 Type: {domain_type.display_name} ({domain_type.name})')
                        
                        # Get phase configuration for this type
                        config = type_configs.get(domain_type.name)
                        if not config:
                            self.stdout.write(self.style.WARNING(f'     ⚠️  No phase config found for "{domain_type.name}"'))
                            continue
                        
                        phases_to_link = config['phases']
                        created_count = 0
                        skipped_count = 0
                        
                        for phase_name, sort_order, is_required in phases_to_link:
                            # Get or create WorkflowPhase
                            workflow_phase, created = WorkflowPhase.objects.get_or_create(
                                name=phase_name,
                                defaults={
                                    'description': f'{phase_name} phase',
                                    'is_active': True,
                                }
                            )
                            
                            # Create DomainPhase link
                            domain_phase, created = DomainPhase.objects.get_or_create(
                                domain_type=domain_type,
                                workflow_phase=workflow_phase,
                                defaults={
                                    'sort_order': sort_order,
                                    'is_active': True,
                                    'is_required': is_required,
                                    'config': {},
                                }
                            )
                            
                            if created:
                                created_count += 1
                                req_marker = '✳️ ' if is_required else '  '
                                self.stdout.write(
                                    f'     {req_marker}✅ Linked: {workflow_phase.name} (order: {sort_order})'
                                )
                            else:
                                skipped_count += 1
                        
                        total_links += created_count
                        
                        if skipped_count > 0:
                            self.stdout.write(
                                self.style.WARNING(f'     ℹ️  Skipped {skipped_count} existing links')
                            )
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'     📊 Created {created_count} new phase links')
                        )

                # Summary
                self.stdout.write('\n' + '=' * 60)
                self.stdout.write(self.style.SUCCESS(f'✅ Successfully linked {total_links} DomainPhases'))
                self.stdout.write('=' * 60)
                
                # Statistics
                self.stdout.write('\n📊 Statistics:')
                self.stdout.write(f'   • Total DomainPhases: {DomainPhase.objects.count()}')
                self.stdout.write(f'   • Active WorkflowPhases: {WorkflowPhase.objects.filter(is_active=True).count()}')
                self.stdout.write(f'   • Active DomainTypes: {DomainType.objects.filter(is_active=True).count()}')
                self.stdout.write('')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}'))
            raise
