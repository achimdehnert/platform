"""
Fix book_chapters VIEW to have project_id column
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fix book_chapters VIEW to include project_id"

    def add_arguments(self, parser):
        parser.add_argument(
            "--strategy",
            type=str,
            default="map",
            choices=["map", "redirect"],
            help="Fix strategy: map (book_id->project_id) or redirect (use writing_chapters)",
        )

    def handle(self, *args, **options):
        strategy = options["strategy"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🔧 FIX book_chapters VIEW"))
        self.stdout.write("=" * 80 + "\n")

        if strategy == "map":
            self.fix_with_mapping()
        else:
            self.fix_with_redirect()

        # Verify fix
        self.verify_fix()

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ FIX COMPLETE!"))
        self.stdout.write("=" * 80 + "\n")

    def fix_with_mapping(self):
        """Create VIEW with column mapping: book_id AS project_id"""
        self.stdout.write("Strategy: Column Mapping (book_id → project_id)\n")

        with connection.cursor() as cursor:
            # Drop existing VIEW
            self.stdout.write("1. Dropping old VIEW book_chapters...")
            cursor.execute("DROP VIEW IF EXISTS book_chapters")
            self.stdout.write(self.style.SUCCESS("   ✅ Dropped\n"))

            # Create new VIEW with mapping
            self.stdout.write("2. Creating new VIEW with column mapping...")
            sql = """
                CREATE VIEW book_chapters AS
                SELECT
                    id,
                    title,
                    number,
                    content,
                    summary,
                    notes,
                    status,
                    word_count,
                    word_count_target,
                    ai_generated,
                    generation_prompt,
                    settings,
                    created_at,
                    updated_at,
                    book_id,
                    book_id AS project_id  -- Map book_id to project_id
                FROM chapters_v2
            """
            cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS("   ✅ Created\n"))

    def fix_with_redirect(self):
        """Redirect VIEW to writing_chapters table"""
        self.stdout.write("Strategy: Redirect to writing_chapters\n")

        with connection.cursor() as cursor:
            # Drop existing VIEW
            self.stdout.write("1. Dropping old VIEW book_chapters...")
            cursor.execute("DROP VIEW IF EXISTS book_chapters")
            self.stdout.write(self.style.SUCCESS("   ✅ Dropped\n"))

            # Create new VIEW pointing to writing_chapters
            self.stdout.write("2. Creating new VIEW → writing_chapters...")
            sql = """
                CREATE VIEW book_chapters AS
                SELECT
                    id,
                    title,
                    chapter_number AS number,
                    content,
                    summary,
                    notes,
                    status,
                    word_count,
                    target_word_count AS word_count_target,
                    created_at,
                    updated_at,
                    project_id
                FROM writing_chapters
            """
            cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS("   ✅ Created\n"))

    def verify_fix(self):
        """Verify the fix worked"""
        self.stdout.write("\n3. Verifying fix...")

        with connection.cursor() as cursor:
            # Check if project_id column exists
            cursor.execute("PRAGMA table_info(book_chapters)")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]

            if "project_id" in col_names:
                self.stdout.write(self.style.SUCCESS("   ✅ project_id column found!"))

                # Show schema
                self.stdout.write("\n   New schema:")
                for col in columns:
                    self.stdout.write(f"      - {col[1]}")
            else:
                self.stdout.write(self.style.ERROR("   ❌ project_id column NOT found!"))
                self.stdout.write("\n   Available columns:")
                for col in columns:
                    self.stdout.write(f"      - {col[1]}")
