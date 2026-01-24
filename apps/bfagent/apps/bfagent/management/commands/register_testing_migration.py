"""
Register Testing Models Migration in Migration Registry

Auto-registers the new testing models migration with metadata.
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models import MigrationRegistry
import hashlib
from pathlib import Path


class Command(BaseCommand):
    help = 'Register testing models migration in Migration Registry'

    def handle(self, *args, **options):
        migration_file = Path('apps/bfagent/migrations/0052_add_testing_models_sqlite_compatible.py')
        
        if not migration_file.exists():
            self.stdout.write(self.style.ERROR(f'Migration file not found: {migration_file}'))
            return
        
        # Calculate file hash
        content = migration_file.read_text(encoding='utf-8')
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Register migration
        migration, created = MigrationRegistry.objects.update_or_create(
            app_label='bfagent',
            migration_name='0052_add_testing_models_sqlite_compatible',
            defaults={
                'migration_number': 52,
                'file_path': str(migration_file),
                'file_hash': file_hash,
                'description': 'Add Testing & Requirements Management System - TestRequirement, TestCase, TestExecution, TestSession, RequirementTestLink, TestCoverageReport',
                'migration_type': 'schema',
                'complexity_score': 30,
                'is_reversible': True,
                'requires_downtime': False,
                'models_created': [
                    'TestRequirement',
                    'TestCase',
                    'RequirementTestLink',
                    'TestExecution',
                    'TestSession',
                    'TestLog',
                    'TestScreenshot',
                    'TestBug',
                    'TestCoverageReport',
                ],
                'models_deleted': [],
                'fields_added': {},
                'fields_removed': {},
                'fields_modified': {},
                'depends_on': [],
                'estimated_affected_rows': 0,
                'estimated_duration_seconds': 2,
                'warnings': [
                    'New tables will be created',
                    'Uses JSONField for tags (was ArrayField in PostgreSQL)',
                    '9 new models will be added',
                    '9 new indexes will be created',
                ],
                'rollback_risks': [
                    'All test data will be lost if rolled back',
                ],
                'is_applied': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Registered migration: {migration.migration_name}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Updated existing migration registration: {migration.migration_name}'
                )
            )
        
        # Print summary
        self.stdout.write('\n📋 Migration Details:')
        self.stdout.write(f'  Type: {migration.migration_type}')
        self.stdout.write(f'  Complexity: {migration.complexity_score}/100')
        self.stdout.write(f'  Reversible: {migration.is_reversible}')
        self.stdout.write(f'  Models Created: {len(migration.models_created)}')
        self.stdout.write(f'  Estimated Time: {migration.estimated_duration_seconds}s')
        self.stdout.write(f'  Applied: {migration.is_applied}')
