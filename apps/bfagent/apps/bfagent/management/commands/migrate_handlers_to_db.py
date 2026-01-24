"""
Management command to migrate Handler Registries to DB
Converts HandlerRegistry (code) → Handler Model (database)
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models_handlers import Handler
from apps.bfagent.services.handlers.registries import (
    InputHandlerRegistry,
    ProcessingHandlerRegistry,
    OutputHandlerRegistry
)


class Command(BaseCommand):
    help = 'Migrate Handler Registries to Database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if handlers already exist',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(self.style.SUCCESS(
            '='*70
        ))
        self.stdout.write(self.style.SUCCESS(
            'MIGRATING HANDLER REGISTRIES TO DATABASE'
        ))
        self.stdout.write(self.style.SUCCESS(
            '='*70
        ))
        self.stdout.write()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '🔍 DRY RUN MODE - No changes will be made'
            ))
            self.stdout.write()

        # Migrate Input Handlers
        self.migrate_registry(
            registry=InputHandlerRegistry,
            category='input',
            dry_run=dry_run,
            force=force
        )

        # Migrate Processing Handlers
        self.migrate_registry(
            registry=ProcessingHandlerRegistry,
            category='processing',
            dry_run=dry_run,
            force=force
        )

        # Migrate Output Handlers
        self.migrate_registry(
            registry=OutputHandlerRegistry,
            category='output',
            dry_run=dry_run,
            force=force
        )

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS(
            '='*70
        ))
        self.stdout.write(self.style.SUCCESS(
            '✅ MIGRATION COMPLETE!'
        ))
        self.stdout.write(self.style.SUCCESS(
            '='*70
        ))

        if not dry_run:
            # Show summary
            total = Handler.objects.count()
            active = Handler.objects.filter(is_active=True).count()
            self.stdout.write()
            self.stdout.write(f"📊 Total Handlers: {total}")
            self.stdout.write(f"✅ Active Handlers: {active}")
            self.stdout.write()
            self.stdout.write(self.style.SUCCESS(
                "🚀 Handler system ready! Run 'python manage.py makemigrations' and 'python manage.py migrate' if needed."
            ))

    def migrate_registry(self, registry, category: str, dry_run: bool = False, force: bool = False):
        """Migrate handlers from a registry to database"""
        
        self.stdout.write(self.style.HTTP_INFO(
            f'\n📦 Migrating {category.upper()} Handlers...'
        ))
        self.stdout.write('-'*70)

        handlers_dict = registry._handlers
        
        if not handlers_dict:
            self.stdout.write(self.style.WARNING(
                f'  ⚠️  No handlers found in {category} registry'
            ))
            return

        migrated = 0
        skipped = 0
        errors = 0

        for handler_id, handler_class in handlers_dict.items():
            try:
                # Extract handler metadata
                display_name = getattr(handler_class, 'display_name', handler_id)
                description = getattr(handler_class, 'description', '')
                version = getattr(handler_class, 'version', '1.0.0')
                
                # Module and class info
                module_path = handler_class.__module__
                class_name = handler_class.__name__
                
                # Schemas
                config_schema = getattr(handler_class, 'config_schema', {})
                input_schema = getattr(handler_class, 'input_schema', {})
                output_schema = getattr(handler_class, 'output_schema', {})
                
                # Metadata
                requires_llm = getattr(handler_class, 'requires_llm', False)
                example_config = getattr(handler_class, 'example_config', {})

                # Check if already exists
                existing = Handler.objects.filter(handler_id=handler_id).first()
                
                if existing and not force:
                    self.stdout.write(self.style.WARNING(
                        f'  ⏭️  {handler_id}: Already exists (use --force to update)'
                    ))
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(self.style.MIGRATE_HEADING(
                        f'  📝 Would create/update: {handler_id}'
                    ))
                    self.stdout.write(f'      Display Name: {display_name}')
                    self.stdout.write(f'      Module: {module_path}')
                    self.stdout.write(f'      Class: {class_name}')
                    migrated += 1
                    continue

                # Create or update handler
                handler, created = Handler.objects.update_or_create(
                    handler_id=handler_id,
                    defaults={
                        'display_name': display_name,
                        'description': description,
                        'category': category,
                        'module_path': module_path,
                        'class_name': class_name,
                        'config_schema': config_schema,
                        'input_schema': input_schema,
                        'output_schema': output_schema,
                        'version': version,
                        'requires_llm': requires_llm,
                        'example_config': example_config,
                        'is_active': True,
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✅ {handler_id}: Created'
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'  🔄 {handler_id}: Updated'
                    ))
                
                migrated += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  ❌ {handler_id}: ERROR - {str(e)}'
                ))
                errors += 1

        # Summary
        self.stdout.write()
        self.stdout.write(f'  ✅ Migrated: {migrated}')
        if skipped > 0:
            self.stdout.write(f'  ⏭️  Skipped: {skipped}')
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'  ❌ Errors: {errors}'))
