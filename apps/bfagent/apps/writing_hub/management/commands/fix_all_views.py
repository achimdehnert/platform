"""
Fix all VIEW mappings automatically
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fix all VIEW column mappings"

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🔧 FIX ALL VIEWS"))
        self.stdout.write("=" * 80 + "\n")

        # Fix book_chapters
        self.fix_book_chapters()

        # Fix book_projects
        self.fix_book_projects()

        # Fix characters (if needed)
        self.fix_characters()

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ ALL VIEWS FIXED!"))
        self.stdout.write("=" * 80 + "\n")

    def fix_book_chapters(self):
        """Fix book_chapters VIEW with correct column mapping"""
        self.stdout.write("1. Fixing book_chapters VIEW...")

        with connection.cursor() as cursor:
            # Drop existing
            cursor.execute("DROP VIEW IF EXISTS book_chapters")

            # Create with COMPLETE mapping from writing_chapters
            sql = """
                CREATE VIEW book_chapters AS
                SELECT
                    id,
                    title,
                    summary,
                    content,
                    chapter_number,
                    chapter_number AS number,  -- For generated model compatibility
                    status,
                    word_count,
                    target_word_count,
                    target_word_count AS word_count_target,  -- For generated model
                    notes,
                    outline,              -- MISSING BEFORE!
                    created_at,
                    updated_at,
                    writing_stage,
                    content_hash,
                    metadata,
                    ai_suggestions,
                    consistency_score,
                    mood_tone,
                    setting_location,
                    time_period,
                    character_arcs,
                    ai_generated_outline,
                    ai_generated_draft,
                    ai_generated_summary,
                    ai_dialogue_suggestions,
                    ai_prose_improvements,
                    ai_scene_expansions,
                    ai_generation_history,
                    project_id,
                    story_arc_id
                FROM writing_chapters
            """
            cursor.execute(sql)

            self.stdout.write(self.style.SUCCESS("   ✅ book_chapters fixed"))

            # Verify
            cursor.execute("PRAGMA table_info(book_chapters)")
            cols = cursor.fetchall()
            col_names = [col[1] for col in cols]

            required = ["id", "number", "chapter_number", "project_id", "title", "outline"]
            missing = [c for c in required if c not in col_names]

            if missing:
                self.stdout.write(self.style.ERROR(f"   ⚠️  Missing columns: {missing}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"   ✅ All {len(col_names)} columns present"))

    def fix_book_projects(self):
        """Fix book_projects VIEW with correct column mapping"""
        self.stdout.write("\n2. Fixing book_projects VIEW...")

        with connection.cursor() as cursor:
            # Drop existing
            cursor.execute("DROP VIEW IF EXISTS book_projects")

            # Create with complete mapping from writing_book_projects
            sql = """
                CREATE VIEW book_projects AS
                SELECT
                    id,
                    user_id,
                    title,
                    genre_id AS genre,  -- Map genre_id to genre for generated model
                    content_rating,
                    description,
                    tagline,
                    target_word_count,
                    current_word_count,
                    status_id AS status,
                    deadline,
                    created_at,
                    updated_at,
                    story_premise,
                    target_audience,
                    story_themes,
                    setting_time,
                    setting_location,
                    atmosphere_tone,
                    main_conflict,
                    stakes,
                    protagonist_concept,
                    antagonist_concept,
                    inspiration_sources,
                    unique_elements,
                    genre_settings,
                    book_type_id,
                    owner_id,
                    workflow_template_id,
                    current_phase_step_id
                FROM writing_book_projects
            """
            cursor.execute(sql)

            self.stdout.write(self.style.SUCCESS("   ✅ book_projects fixed"))

    def fix_characters(self):
        """Fix characters VIEW if needed"""
        self.stdout.write("\n3. Checking characters VIEW...")

        with connection.cursor() as cursor:
            # Check if characters exists
            cursor.execute("SELECT type FROM sqlite_master WHERE name = 'characters'")
            result = cursor.fetchone()

            if not result:
                # Create VIEW to characters_v2
                self.stdout.write("   Creating characters VIEW...")
                cursor.execute("DROP VIEW IF EXISTS characters")
                cursor.execute("CREATE VIEW characters AS SELECT * FROM characters_v2")
                self.stdout.write(self.style.SUCCESS("   ✅ characters VIEW created"))
            else:
                self.stdout.write(self.style.SUCCESS("   ✅ characters already exists"))
