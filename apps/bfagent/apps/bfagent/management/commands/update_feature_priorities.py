"""
Django Management Command: Update feature priorities from medium to backlog
"""
from django.core.management.base import BaseCommand
from apps.bfagent.models import ComponentRegistry


class Command(BaseCommand):
    help = 'Update all features with priority=medium to priority=backlog'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write("=" * 80)
        self.stdout.write("UPDATE FEATURE PRIORITIES: medium → backlog")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            self.stdout.write("")

        # Find all features with priority=medium
        medium_features = ComponentRegistry.objects.filter(priority='medium')
        count = medium_features.count()

        self.stdout.write(f"Found {count} features with priority='medium'")
        self.stdout.write("")

        if count == 0:
            self.stdout.write(self.style.SUCCESS("✅ No features need updating!"))
            return

        # Show first 10 as preview
        self.stdout.write("Preview (first 10):")
        for feature in medium_features[:10]:
            self.stdout.write(f"  • {feature.name} ({feature.component_type}) - {feature.status}")

        if count > 10:
            self.stdout.write(f"  ... and {count - 10} more")

        self.stdout.write("")

        if not dry_run:
            # Confirm action
            self.stdout.write(self.style.WARNING(f"About to update {count} features..."))
            
            # Perform update
            updated = medium_features.update(priority='backlog')
            
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated} features from 'medium' to 'backlog'"))
            self.stdout.write("")
            self.stdout.write("Next steps:")
            self.stdout.write("1. Review features at: http://localhost:8000/control-center/feature-planning/")
            self.stdout.write("2. Prioritize important features manually")
        else:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would update {count} features"))
            self.stdout.write("")
            self.stdout.write("Run without --dry-run to apply changes:")
            self.stdout.write("  python manage.py update_feature_priorities")
