"""
Create Demo Phases for GenAgent Testing

Management command to create sample phases for testing the Action CRUD system
"""

from django.core.management.base import BaseCommand
from apps.genagent.models import Phase


class Command(BaseCommand):
    help = 'Create demo phases for GenAgent testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating demo phases...'))

        phases_data = [
            {
                'name': 'Preparation',
                'description': 'Initial setup and data gathering phase',
                'order': 1,
                'color': '#3B82F6',  # Blue
                'is_active': True
            },
            {
                'name': 'Validation',
                'description': 'Data validation and quality checks',
                'order': 2,
                'color': '#10B981',  # Green
                'is_active': True
            },
            {
                'name': 'Processing',
                'description': 'Main data processing and transformation',
                'order': 3,
                'color': '#F59E0B',  # Amber
                'is_active': True
            },
            {
                'name': 'Output',
                'description': 'Results generation and delivery',
                'order': 4,
                'color': '#8B5CF6',  # Purple
                'is_active': True
            }
        ]

        created_count = 0
        updated_count = 0

        for phase_data in phases_data:
            phase, created = Phase.objects.update_or_create(
                name=phase_data['name'],
                defaults=phase_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created phase: {phase.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'→ Updated phase: {phase.name}')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {created_count} phases, updated {updated_count} phases.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total phases in database: {Phase.objects.count()}'
        ))
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('1. Visit http://127.0.0.1:8000/genagent/actions/')
        self.stdout.write('2. Click "Add Action" on any phase')
        self.stdout.write('3. Select a handler and see dynamic config generation!')
