"""
Management command to sync registered handlers to database.

This command reads all registered handlers from the handler registries
(InputHandlerRegistry, ProcessingHandlerRegistry, OutputHandlerRegistry)
and creates/updates corresponding Handler records in the database.

Usage:
    python manage.py sync_handlers
    python manage.py sync_handlers --dry-run
    python manage.py sync_handlers --force
"""
import inspect
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Handler, HandlerCategory
from apps.bfagent.services.handlers.registries import (
    InputHandlerRegistry,
    ProcessingHandlerRegistry,
    OutputHandlerRegistry,
)


class Command(BaseCommand):
    help = "Synchronize registered handlers to database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be synced without making changes",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update existing handlers",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("  🔄 HANDLER SYNCHRONIZATION"))
        self.stdout.write("=" * 70 + "\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("  🔍 DRY RUN MODE - No changes will be made"))
            self.stdout.write("")

        # Get categories
        try:
            input_cat = HandlerCategory.objects.get(code="input")
            processing_cat = HandlerCategory.objects.get(code="processing")
            output_cat = HandlerCategory.objects.get(code="output")
        except HandlerCategory.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"\n❌ ERROR: {e}"))
            self.stdout.write(self.style.ERROR("   Run: python manage.py load_handler_categories\n"))
            return

        # Registry mapping
        registries = [
            ("input", InputHandlerRegistry, input_cat),
            ("processing", ProcessingHandlerRegistry, processing_cat),
            ("output", OutputHandlerRegistry, output_cat),
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for category_code, registry, category in registries:
            self.stdout.write(f"\n📦 Processing {category_code.upper()} handlers...")
            self.stdout.write("-" * 70)

            handlers = registry.list_handlers()
            
            if not handlers:
                self.stdout.write(f"  ℹ️  No {category_code} handlers registered")
                continue

            for handler_name in handlers:
                try:
                    handler_class = registry.get(handler_name)
                    
                    # Extract handler info
                    module_path = handler_class.__module__
                    class_name = handler_class.__name__
                    description = handler_class.__doc__ or ""
                    description = description.strip().split("\n")[0] if description else ""
                    
                    # Check if exists
                    existing = Handler.objects.filter(code=handler_name).first()
                    
                    if existing and not force:
                        self.stdout.write(
                            f"  ⏭️  {handler_name} - Already exists (use --force to update)"
                        )
                        skipped_count += 1
                        continue

                    if dry_run:
                        action = "UPDATE" if existing else "CREATE"
                        self.stdout.write(
                            f"  🔍 [{action}] {handler_name}"
                        )
                        self.stdout.write(f"       Module: {module_path}")
                        self.stdout.write(f"       Class: {class_name}")
                        if existing:
                            updated_count += 1
                        else:
                            created_count += 1
                        continue

                    # Create/Update handler
                    with transaction.atomic():
                        handler, created = Handler.objects.update_or_create(
                            code=handler_name,
                            defaults={
                                "name": handler_name.replace("_", " ").title(),
                                "description": description[:500] if description else f"{class_name} handler",
                                "category": category_code,  # Old CharField
                                "category_fk": category,     # New ForeignKey
                                "module_path": module_path,
                                "class_name": class_name,
                                "is_active": True,
                                "version": "1.0.0",
                            },
                        )

                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(f"  ✅ CREATED: {handler_name}")
                            )
                            created_count += 1
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(f"  🔄 UPDATED: {handler_name}")
                            )
                            updated_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ ERROR syncing {handler_name}: {e}")
                    )

        # Summary
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("  📊 SYNCHRONIZATION SUMMARY"))
        self.stdout.write("=" * 70)
        
        if dry_run:
            self.stdout.write(f"  Would CREATE: {created_count}")
            self.stdout.write(f"  Would UPDATE: {updated_count}")
        else:
            self.stdout.write(f"  ✅ Created: {created_count}")
            self.stdout.write(f"  🔄 Updated: {updated_count}")
        
        self.stdout.write(f"  ⏭️  Skipped: {skipped_count}")
        
        total = Handler.objects.count()
        self.stdout.write(f"\n  📦 Total handlers in DB: {total}")
        
        self.stdout.write("\n" + "=" * 70)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n💡 Run without --dry-run to apply changes\n"))
        else:
            self.stdout.write(self.style.SUCCESS("\n🎉 SYNC COMPLETE!\n"))

            # Verify migration status
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write("  🔍 MIGRATION VERIFICATION")
            self.stdout.write("=" * 70)
            
            migrated = Handler.objects.exclude(category_fk=None).count()
            not_migrated = Handler.objects.filter(category_fk=None).count()
            
            self.stdout.write(f"  ✅ Migrated (category_fk set): {migrated}/{total}")
            self.stdout.write(f"  ❌ Not migrated: {not_migrated}/{total}")
            
            if not_migrated > 0:
                self.stdout.write(
                    self.style.WARNING(f"\n  ⚠️  {not_migrated} handlers need migration!")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("\n  ✅ All handlers have category_fk set!")
                )
            
            self.stdout.write("\n" + "=" * 70 + "\n")
