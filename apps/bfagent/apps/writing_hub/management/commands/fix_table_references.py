"""
Auto-fix incorrect table references
Creates aliases for missing tables or updates model references
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Auto-fix missing table references by creating views or renaming tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without executing",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🔧 AUTO-FIX TABLE REFERENCES"))
        self.stdout.write("=" * 80 + "\n")

        fixes = [
            {
                "missing": "book_chapters",
                "actual": "chapters_v2",
                "action": "create_view",
                "description": "Create VIEW book_chapters → chapters_v2",
            },
            {
                "missing": "book_projects",
                "actual": "writing_book_projects",
                "action": "create_view",
                "description": "Create VIEW book_projects → writing_book_projects",
            },
        ]

        for fix in fixes:
            self.stdout.write(f"\n📋 {fix['description']}")

            if dry_run:
                self.stdout.write(f"   [DRY RUN] Would execute:")
                sql = self.get_fix_sql(fix)
                self.stdout.write(f"   {sql}")
            else:
                try:
                    self.execute_fix(fix)
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Success!"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Failed: {e}"))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("🎉 Done!")
        self.stdout.write("=" * 80 + "\n")

    def get_fix_sql(self, fix):
        """Get SQL for the fix"""
        if fix["action"] == "create_view":
            return f"CREATE VIEW IF NOT EXISTS {fix['missing']} AS SELECT * FROM {fix['actual']}"
        return ""

    def execute_fix(self, fix):
        """Execute the fix"""
        with connection.cursor() as cursor:
            if fix["action"] == "create_view":
                sql = f"CREATE VIEW IF NOT EXISTS {fix['missing']} AS SELECT * FROM {fix['actual']}"
                cursor.execute(sql)
                self.stdout.write(f"   Created view: {fix['missing']}")
