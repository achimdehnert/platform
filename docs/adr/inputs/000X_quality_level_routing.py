"""
aifw/migrations/000X_quality_level_routing.py

ADR-097 §3 — Complete migration for aifw 0.6.0.

BEFORE APPLYING:
    Replace "000W_previous_migration" with the actual predecessor migration name.
    Run: python manage.py showmigrations aifw | tail -1

Operations:
    1. Add quality_level, priority, prompt_template_key to AIActionType
    2. ADD CHECK constraint on priority column (values or NULL)
    3. CREATE 4 partial unique indexes (B-01 fix — PostgreSQL NULL semantics)
    4. CREATE TierQualityMapping table
    5. SEED default TierQualityMapping rows (premium=8, pro=5, freemium=2)
    6. Add quality_level column to AIUsageLog (OQ-2)

Safe to apply on existing DB with data — all operations are additive/nullable.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # !! Replace with actual predecessor migration !!
        ("aifw", "000W_previous_migration"),
    ]

    operations = [

        # ── 1. Add nullable columns to AIActionType ───────────────────────────
        migrations.AddField(
            model_name="aiactiontype",
            name="quality_level",
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="aiactiontype",
            name="priority",
            field=models.CharField(max_length=16, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="aiactiontype",
            name="prompt_template_key",
            field=models.CharField(max_length=128, null=True, blank=True),
        ),

        # ── 2. CHECK constraint on priority column (M-02 fix) ─────────────────
        # Prevents typos like "qulaity" from silently becoming catch-all rows.
        migrations.RunSQL(
            sql="""
                ALTER TABLE aifw_aiactiontype
                ADD CONSTRAINT chk_aiaction_priority
                CHECK (priority IN ('fast', 'balanced', 'quality') OR priority IS NULL);
            """,
            reverse_sql="""
                ALTER TABLE aifw_aiactiontype
                DROP CONSTRAINT IF EXISTS chk_aiaction_priority;
            """,
        ),

        # ── 3. Four partial unique indexes (B-01 fix) ─────────────────────────
        #
        # Rationale: Standard UNIQUE(code, quality_level, priority) fails in PostgreSQL
        # because NULL != NULL per ISO/IEC 9075. Two rows with (code=X, NULL, NULL)
        # do NOT violate UNIQUE — the DB allows duplicates silently.
        #
        # Four partial indexes cover all NULL/NOT-NULL combinations exactly:
        #   Exact:     both non-NULL → unique on all three
        #   QL-only:   quality_level non-NULL, priority NULL → unique on (code, ql)
        #   Prio-only: priority non-NULL, quality_level NULL → unique on (code, prio)
        #   Catchall:  both NULL → unique on (code) alone
        #
        # Each index name (uix_aiaction_*) is referenced in tests — do not rename.

        migrations.RunSQL(
            # Exact match rows — both dimensions specified
            sql="""
                CREATE UNIQUE INDEX uix_aiaction_exact
                ON aifw_aiactiontype (code, quality_level, priority)
                WHERE quality_level IS NOT NULL AND priority IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS uix_aiaction_exact;",
        ),
        migrations.RunSQL(
            # Level-only rows — priority is catch-all, quality_level must be set
            sql="""
                CREATE UNIQUE INDEX uix_aiaction_ql_only
                ON aifw_aiactiontype (code, quality_level)
                WHERE quality_level IS NOT NULL AND priority IS NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS uix_aiaction_ql_only;",
        ),
        migrations.RunSQL(
            # Priority-only rows — quality is catch-all, priority must be set
            sql="""
                CREATE UNIQUE INDEX uix_aiaction_prio_only
                ON aifw_aiactiontype (code, priority)
                WHERE quality_level IS NULL AND priority IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS uix_aiaction_prio_only;",
        ),
        migrations.RunSQL(
            # Full catch-all rows — both NULL (legacy rows + default fallback)
            sql="""
                CREATE UNIQUE INDEX uix_aiaction_catchall
                ON aifw_aiactiontype (code)
                WHERE quality_level IS NULL AND priority IS NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS uix_aiaction_catchall;",
        ),

        # ── 4. Create TierQualityMapping table ────────────────────────────────
        migrations.CreateModel(
            name="TierQualityMapping",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False),
                ),
                (
                    "tier",
                    models.CharField(max_length=64, unique=True),
                ),
                (
                    "quality_level",
                    models.IntegerField(),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, db_index=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
            ],
            options={
                "verbose_name": "Tier Quality Mapping",
                "verbose_name_plural": "Tier Quality Mappings",
                "app_label": "aifw",
                "ordering": ["-quality_level"],
            },
        ),

        # ── 5. Seed default TierQualityMapping rows ───────────────────────────
        # ON CONFLICT DO NOTHING — safe to re-run (idempotent).
        # QualityLevel: PREMIUM=8, BALANCED=5, ECONOMY=2
        migrations.RunSQL(
            sql="""
                INSERT INTO aifw_tierqualitymapping
                    (tier, quality_level, is_active, created_at, updated_at)
                VALUES
                    ('premium',  8, TRUE, NOW(), NOW()),
                    ('pro',      5, TRUE, NOW(), NOW()),
                    ('freemium', 2, TRUE, NOW(), NOW())
                ON CONFLICT (tier) DO NOTHING;
            """,
            reverse_sql="""
                DELETE FROM aifw_tierqualitymapping
                WHERE tier IN ('premium', 'pro', 'freemium');
            """,
        ),

        # ── 6. Add quality_level to AIUsageLog (OQ-2 resolved) ───────────────
        # Dedicated column — never join to AIActionType for cost analytics.
        # NULL for all existing rows created before 0.6.0.
        migrations.AddField(
            model_name="aiusagelog",
            name="quality_level",
            field=models.IntegerField(
                null=True,
                blank=True,
                db_index=True,
                help_text="Quality level of the request (1–9). NULL for pre-0.6.0 entries.",
            ),
        ),
    ]
