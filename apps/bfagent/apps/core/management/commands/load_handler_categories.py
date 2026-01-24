"""
Management Command: Load Handler Categories

Loads initial/default handler categories into the database.

Usage:
    python manage.py load_handler_categories
    python manage.py load_handler_categories --reset  # Delete existing first
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import HandlerCategory


class Command(BaseCommand):
    help = "Load default handler categories into database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing categories first (WARNING: cascades to handlers!)",
        )

    def handle(self, *args, **options):
        reset = options.get("reset", False)

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("  LOAD HANDLER CATEGORIES")
        self.stdout.write("=" * 70 + "\n")

        if reset:
            self.stdout.write(self.style.WARNING("⚠️  RESET MODE: Deleting existing categories..."))

            # Only delete non-system categories in reset mode
            deleted_count = HandlerCategory.objects.filter(is_system=False).count()
            HandlerCategory.objects.filter(is_system=False).delete()

            self.stdout.write(
                self.style.SUCCESS(f"✅ Deleted {deleted_count} non-system categories\n")
            )

        # Get default categories
        default_categories = HandlerCategory.get_default_categories()

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for cat_data in default_categories:
                code = cat_data["code"]

                try:
                    category, created = HandlerCategory.objects.get_or_create(
                        code=code, defaults=cat_data
                    )

                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Created: {category.name} ({category.code})")
                        )
                        created_count += 1
                    else:
                        # Update existing if values changed
                        updated = False
                        for key, value in cat_data.items():
                            if key == "code":
                                continue
                            if getattr(category, key) != value:
                                setattr(category, key, value)
                                updated = True

                        if updated:
                            category.save()
                            self.stdout.write(
                                self.style.WARNING(f"🔄 Updated: {category.name} ({category.code})")
                            )
                            updated_count += 1
                        else:
                            self.stdout.write(
                                f"⏭️  Skipped: {category.name} ({category.code}) - unchanged"
                            )
                            skipped_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Error with {code}: {e}"))

        # Summary
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("  SUMMARY")
        self.stdout.write("=" * 70 + "\n")

        self.stdout.write(self.style.SUCCESS(f"✅ Created: {created_count}"))
        self.stdout.write(self.style.WARNING(f"🔄 Updated: {updated_count}"))
        self.stdout.write(f"⏭️  Skipped: {skipped_count}")
        self.stdout.write(f"📊 Total: {created_count + updated_count + skipped_count}\n")

        # Show current state
        total = HandlerCategory.objects.count()
        active = HandlerCategory.objects.filter(is_active=True).count()
        system = HandlerCategory.objects.filter(is_system=True).count()

        self.stdout.write(f"Database State:")
        self.stdout.write(f"  Total Categories: {total}")
        self.stdout.write(f"  Active: {active}")
        self.stdout.write(f"  System: {system}\n")

        self.stdout.write(self.style.SUCCESS("✅ Handler categories loaded successfully!"))
