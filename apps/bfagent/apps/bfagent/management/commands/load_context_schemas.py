"""
Management Command: load_context_schemas

Pre-loads default context enrichment schemas into the database.
These schemas are marked as is_system=True and cannot be deleted via UI.

Usage:
    python manage.py load_context_schemas
    python manage.py load_context_schemas --force  # Re-create all schemas
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bfagent.models import ContextSchema, ContextSource
from apps.bfagent.services.context_enrichment.presets import DEFAULT_SCHEMAS


class Command(BaseCommand):
    help = 'Load default context enrichment schemas into database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-creation of all schemas (deletes existing)',
        )
        parser.add_argument(
            '--schema',
            type=str,
            help='Load only specific schema by name',
        )

    def handle(self, *args, **options):
        force = options['force']
        specific_schema = options.get('schema')

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Loading Context Enrichment Schemas'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # Filter schemas if specific one requested
        schemas_to_load = DEFAULT_SCHEMAS
        if specific_schema:
            schemas_to_load = [
                s for s in DEFAULT_SCHEMAS
                if s['name'] == specific_schema
            ]
            if not schemas_to_load:
                raise CommandError(
                    f"Schema '{specific_schema}' not found in presets"
                )

        # Load each schema
        for schema_data in schemas_to_load:
            self._load_schema(schema_data, force)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Successfully loaded {len(schemas_to_load)} schema(s)'
            )
        )
        self.stdout.write(self.style.SUCCESS('=' * 70))

    @transaction.atomic
    def _load_schema(self, schema_data: dict, force: bool = False):
        """
        Load or update a single schema.

        Args:
            schema_data: Schema configuration dict
            force: If True, delete existing schema first
        """
        schema_name = schema_data['name']
        sources_data = schema_data.pop('sources', [])

        self.stdout.write('')
        self.stdout.write(f"Processing schema: {schema_name}")
        self.stdout.write('-' * 70)

        # Check if schema exists
        existing_schema = ContextSchema.objects.filter(name=schema_name).first()

        if existing_schema:
            if force:
                # Delete and recreate
                self.stdout.write(
                    self.style.WARNING(f"  → Deleting existing schema...")
                )
                existing_schema.delete()
                existing_schema = None
            else:
                # Update existing
                self.stdout.write(
                    self.style.WARNING(f"  → Schema exists, updating...")
                )

        if existing_schema:
            # Update schema
            for key, value in schema_data.items():
                setattr(existing_schema, key, value)
            existing_schema.save()
            schema = existing_schema
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Updated schema: {schema.display_name}")
            )
        else:
            # Create new schema
            schema = ContextSchema.objects.create(**schema_data)
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Created schema: {schema.display_name}")
            )

        # Load sources
        self._load_sources(schema, sources_data, force)

        # Validate schema
        from apps.bfagent.services.context_enrichment.validators import SchemaValidator
        validator = SchemaValidator()
        errors = validator.validate(schema)

        if errors:
            self.stdout.write(
                self.style.ERROR(f"  ✗ Schema validation failed:")
            )
            for error in errors:
                self.stdout.write(self.style.ERROR(f"    - {error}"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Schema validation passed")
            )

    def _load_sources(
        self,
        schema: ContextSchema,
        sources_data: list,
        force: bool = False
    ):
        """
        Load sources for a schema.

        Args:
            schema: ContextSchema instance
            sources_data: List of source configuration dicts
            force: If True, delete existing sources first
        """
        if force:
            # Delete all existing sources
            deleted_count = schema.sources.all().delete()[0]
            if deleted_count > 0:
                self.stdout.write(
                    self.style.WARNING(f"    → Deleted {deleted_count} existing sources")
                )

        # Create or update sources
        for source_data in sources_data:
            source_name = source_data['name']

            # Check if source exists
            existing_source = schema.sources.filter(name=source_name).first()

            if existing_source:
                # Update existing
                for key, value in source_data.items():
                    setattr(existing_source, key, value)
                existing_source.save()
                self.stdout.write(f"    ↻ Updated source: {source_name}")
            else:
                # Create new
                ContextSource.objects.create(
                    schema=schema,
                    **source_data
                )
                self.stdout.write(
                    self.style.SUCCESS(f"    ✓ Created source: {source_name}")
                )

        # Summary
        total_sources = schema.sources.filter(is_active=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ Schema has {total_sources} active source(s)"
            )
        )
