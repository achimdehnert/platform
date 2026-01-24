"""
Admin Diagnostics Service - Central service for database schema diagnostics
Integrated into bfagent core functionality (Dec 9, 2025)
Enhanced with Sentry Integration (Dec 9, 2025)
"""

import re
from typing import Any, Dict, List, Tuple

from django.apps import apps
from django.contrib.admin import site
from django.db import connection
from django.test import Client


class AdminDiagnosticsService:
    """
    Central service for Django Admin diagnostics and auto-fixing

    Enhanced with THE COMPLETE DEVOPS AI STACK:
    - Sentry error tracking + AI analysis (Seer)
    - Grafana monitoring + pattern detection (Sift)
    - Chrome DevTools visual testing + performance profiling
    """

    def __init__(self):
        self.client = None
        self.errors = []
        self.fixes_applied = []

        # Initialize Sentry integration
        try:
            from apps.bfagent.services.sentry_integration import get_sentry_service

            self.sentry = get_sentry_service()
        except ImportError:
            self.sentry = None

        # Initialize Grafana integration
        try:
            from apps.bfagent.services.grafana_integration import get_grafana_service

            self.grafana = get_grafana_service()
        except ImportError:
            self.grafana = None

        # Initialize Chrome DevTools integration
        try:
            from apps.bfagent.services.chrome_devtools_integration import get_chrome_service

            self.chrome = get_chrome_service()
        except ImportError:
            self.chrome = None

    # ============================================================================
    # 1. SCHEMA DIAGNOSTICS
    # ============================================================================

    def diagnose_schema_errors(self, app_label: str = None) -> Dict[str, Any]:
        """
        Find schema mismatches between Django models and database tables

        Args:
            app_label: Optional app to limit diagnostics to

        Returns:
            Dict with missing_tables, missing_columns, and recommendations
        """
        results = {
            "missing_tables": [],
            "missing_columns": [],
            "unused_tables": [],
            "recommendations": [],
        }

        # Get all models
        if app_label:
            models = apps.get_app_config(app_label).get_models()
        else:
            models = apps.get_models()

        with connection.cursor() as cursor:
            # Get all actual tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
            actual_tables = {row[0] for row in cursor.fetchall()}

            for model in models:
                table_name = model._meta.db_table

                # Check if table exists
                if table_name not in actual_tables:
                    results["missing_tables"].append(
                        {
                            "model": f"{model._meta.app_label}.{model.__name__}",
                            "table": table_name,
                            "managed": model._meta.managed,
                        }
                    )
                    continue

                # Check columns
                cursor.execute(f"PRAGMA table_info({table_name})")
                actual_columns = {row[1] for row in cursor.fetchall()}

                for field in model._meta.fields:
                    column_name = field.column
                    if column_name not in actual_columns:
                        results["missing_columns"].append(
                            {
                                "model": f"{model._meta.app_label}.{model.__name__}",
                                "table": table_name,
                                "column": column_name,
                                "field": field.name,
                                "type": field.get_internal_type(),
                            }
                        )

        # Generate recommendations
        self._generate_recommendations(results)

        return results

    def find_similar_tables(self, target_table: str) -> List[str]:
        """Find tables with similar names in the database"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [row[0] for row in cursor.fetchall()]

        # Find similar tables
        target_base = target_table.replace("_", "").lower()
        similar = []

        for table in all_tables:
            table_base = table.replace("_", "").lower()
            if target_base in table_base or table_base in target_base:
                similar.append(table)

        return similar

    # ============================================================================
    # 2. AUTO-FIX FUNCTIONALITY
    # ============================================================================

    def fix_table_references(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Auto-fix missing tables by creating VIEWs to similar tables

        Args:
            dry_run: If True, only show what would be done

        Returns:
            Dict with fixes_applied and errors
        """
        results = {"fixes_applied": [], "errors": [], "dry_run": dry_run}

        schema_issues = self.diagnose_schema_errors()

        for missing in schema_issues["missing_tables"]:
            table_name = missing["table"]
            similar = self.find_similar_tables(table_name)

            if similar:
                source_table = similar[0]

                if dry_run:
                    results["fixes_applied"].append(
                        {
                            "action": "CREATE VIEW (dry-run)",
                            "target": table_name,
                            "source": source_table,
                        }
                    )
                else:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(f"DROP VIEW IF EXISTS {table_name}")
                            cursor.execute(
                                f"CREATE VIEW {table_name} AS SELECT * FROM {source_table}"
                            )

                        results["fixes_applied"].append(
                            {"action": "CREATE VIEW", "target": table_name, "source": source_table}
                        )
                    except Exception as e:
                        results["errors"].append({"table": table_name, "error": str(e)})

        return results

    def fix_all_views(self) -> Dict[str, Any]:
        """
        Fix all known VIEW mappings with complete column sets

        Returns:
            Dict with fixed views and errors
        """
        results = {"fixed": [], "errors": []}

        # Fix book_chapters
        try:
            self._fix_book_chapters_view()
            results["fixed"].append("book_chapters")
        except Exception as e:
            results["errors"].append({"view": "book_chapters", "error": str(e)})

        # Fix book_projects
        try:
            self._fix_book_projects_view()
            results["fixed"].append("book_projects")
        except Exception as e:
            results["errors"].append({"view": "book_projects", "error": str(e)})

        # Fix characters
        try:
            self._fix_characters_view()
            results["fixed"].append("characters")
        except Exception as e:
            results["errors"].append({"view": "characters", "error": str(e)})

        return results

    def _fix_book_chapters_view(self):
        """Fix book_chapters VIEW with complete column mapping"""
        with connection.cursor() as cursor:
            cursor.execute("DROP VIEW IF EXISTS book_chapters")
            cursor.execute(
                """
                CREATE VIEW book_chapters AS
                SELECT
                    id, title, summary, content, chapter_number,
                    chapter_number AS number,
                    status, word_count, target_word_count,
                    target_word_count AS word_count_target,
                    notes, outline, created_at, updated_at,
                    writing_stage, content_hash, metadata, ai_suggestions,
                    consistency_score, mood_tone, setting_location, time_period,
                    character_arcs, ai_generated_outline, ai_generated_draft,
                    ai_generated_summary, ai_dialogue_suggestions,
                    ai_prose_improvements, ai_scene_expansions,
                    ai_generation_history, project_id, story_arc_id
                FROM writing_chapters
            """
            )

    def _fix_book_projects_view(self):
        """Fix book_projects VIEW with complete column mapping"""
        with connection.cursor() as cursor:
            cursor.execute("DROP VIEW IF EXISTS book_projects")
            cursor.execute(
                """
                CREATE VIEW book_projects AS
                SELECT
                    id, user_id, title,
                    genre_id AS genre,
                    content_rating, description, tagline,
                    target_word_count, current_word_count,
                    status_id AS status,
                    deadline, created_at, updated_at,
                    story_premise, target_audience, story_themes,
                    setting_time, setting_location, atmosphere_tone,
                    main_conflict, stakes, protagonist_concept,
                    antagonist_concept, inspiration_sources,
                    unique_elements, genre_settings,
                    book_type_id, owner_id, workflow_template_id,
                    current_phase_step_id
                FROM writing_book_projects
            """
            )

    def _fix_characters_view(self):
        """Fix characters VIEW to point to writing_characters"""
        with connection.cursor() as cursor:
            cursor.execute("DROP VIEW IF EXISTS characters")
            cursor.execute("CREATE VIEW characters AS SELECT * FROM writing_characters")

    # ============================================================================
    # 3. ADMIN URL TESTING
    # ============================================================================

    def test_admin_urls(self, app_label: str = None, auto_fix: bool = False) -> Dict[str, Any]:
        """
        Test all admin URLs for a given app

        Args:
            app_label: App to test (e.g., 'writing_hub')
            auto_fix: If True, attempt to auto-fix errors

        Returns:
            Dict with test results and errors
        """
        from django.conf import settings
        from django.contrib.auth import get_user_model

        results = {"tested": [], "errors": [], "fixed": []}

        # Setup test client
        self.client = Client()

        # Temporarily allow test server
        original_allowed_hosts = settings.ALLOWED_HOSTS
        settings.ALLOWED_HOSTS = ["*"]

        try:
            # Get admin user
            User = get_user_model()
            try:
                user = User.objects.first()
                if not user:
                    results["errors"].append(
                        {
                            "error": "No admin user found",
                            "recommendation": "Create superuser: python manage.py createsuperuser",
                        }
                    )
                    return results
            except Exception as e:
                results["errors"].append({"error": f"User lookup failed: {e}"})
                return results

            # Login
            self.client.force_login(user)

            # Get all registered admin models
            for model, model_admin in site._registry.items():
                if app_label and model._meta.app_label != app_label:
                    continue

                url = f"/admin/{model._meta.app_label}/{model._meta.model_name}/"

                try:
                    response = self.client.get(url)

                    if response.status_code == 200:
                        results["tested"].append(
                            {
                                "model": f"{model._meta.app_label}.{model.__name__}",
                                "url": url,
                                "status": "OK",
                            }
                        )
                    else:
                        error_info = self._extract_error_from_response(response)
                        error_data = {
                            "model": f"{model._meta.app_label}.{model.__name__}",
                            "url": url,
                            "status": response.status_code,
                            "error": error_info,
                        }
                        results["errors"].append(error_data)

                        # Send to Sentry
                        if self.sentry and self.sentry.is_enabled():
                            sentry_result = self.sentry.capture_admin_error(
                                error_data, auto_analyze=auto_fix
                            )
                            if sentry_result:
                                error_data["sentry_event_id"] = sentry_result.get("event_id")
                                error_data["sentry_url"] = sentry_result.get("sentry_url")

                        # Auto-fix if requested
                        if auto_fix:
                            fix_result = self._auto_fix_error(error_info)
                            if fix_result:
                                results["fixed"].append(
                                    {
                                        "model": f"{model._meta.app_label}.{model.__name__}",
                                        "fix": fix_result,
                                    }
                                )

                except Exception as e:
                    results["errors"].append(
                        {
                            "model": f"{model._meta.app_label}.{model.__name__}",
                            "url": url,
                            "error": str(e),
                        }
                    )

        finally:
            settings.ALLOWED_HOSTS = original_allowed_hosts

        return results

    def _extract_error_from_response(self, response) -> Dict[str, str]:
        """Extract error information from Django error page"""
        content = response.content.decode("utf-8", errors="ignore")

        error_info = {}

        # Extract OperationalError
        if "OperationalError" in content:
            match = re.search(r"OperationalError: (.+?)(?:<|$)", content)
            if match:
                error_info["type"] = "OperationalError"
                error_info["message"] = match.group(1).strip()

                # Extract missing column/table
                if "no such column:" in error_info["message"]:
                    parts = error_info["message"].split(":")
                    if len(parts) >= 2:
                        column_path = parts[1].strip()
                        if "." in column_path:
                            table, column = column_path.split(".", 1)
                            error_info["table"] = table
                            error_info["column"] = column

                elif "no such table:" in error_info["message"]:
                    parts = error_info["message"].split(":")
                    if len(parts) >= 2:
                        error_info["table"] = parts[1].strip()

        return error_info

    def _auto_fix_error(self, error_info: Dict[str, str]) -> str:
        """Attempt to auto-fix an error"""
        if error_info.get("type") == "OperationalError":
            if "column" in error_info and "table" in error_info:
                # Try to fix missing column by recreating view
                table = error_info["table"]
                if table in ["book_chapters", "book_projects", "characters"]:
                    try:
                        if table == "book_chapters":
                            self._fix_book_chapters_view()
                        elif table == "book_projects":
                            self._fix_book_projects_view()
                        elif table == "characters":
                            self._fix_characters_view()
                        return f"Recreated VIEW {table}"
                    except Exception as e:
                        return f"Failed to fix: {e}"

            elif "table" in error_info:
                # Try to create view to similar table
                table = error_info["table"]
                similar = self.find_similar_tables(table)
                if similar:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(f"DROP VIEW IF EXISTS {table}")
                            cursor.execute(f"CREATE VIEW {table} AS SELECT * FROM {similar[0]}")
                        return f"Created VIEW {table} → {similar[0]}"
                    except Exception as e:
                        return f"Failed to fix: {e}"

        return None

    # ============================================================================
    # 4. UNUSED TABLES DETECTION
    # ============================================================================

    def find_unused_tables(self) -> Dict[str, Any]:
        """
        Find database tables that are not referenced by any Django model

        Returns:
            Dict with used_tables, unused_tables, and statistics
        """
        results = {"used_tables": [], "unused_tables": [], "statistics": {}}

        # Get all Django model tables
        model_tables = set()
        for model in apps.get_models():
            model_tables.add(model._meta.db_table)

        # Get all actual tables
        with connection.cursor() as cursor:
            cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view')")
            all_tables = cursor.fetchall()

            for table_name, table_type in all_tables:
                # Skip Django system tables
                if table_name.startswith("django_") or table_name.startswith("sqlite_"):
                    continue

                is_view = table_type == "view"

                # Get row count
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                except:
                    row_count = 0

                table_info = {"name": table_name, "type": table_type, "rows": row_count}

                if table_name in model_tables:
                    results["used_tables"].append(table_info)
                else:
                    results["unused_tables"].append(table_info)

        # Calculate statistics
        results["statistics"] = {
            "total_tables": len(all_tables),
            "used_tables": len(results["used_tables"]),
            "unused_tables": len(results["unused_tables"]),
            "unused_rows": sum(t["rows"] for t in results["unused_tables"]),
        }

        return results

    # ============================================================================
    # ULTIMATE HEALTH CHECK (All 3 MCPs Combined!)
    # ============================================================================

    def ultimate_health_check(
        self, app_label: str = None, auto_fix: bool = False, visual_testing: bool = False
    ) -> Dict[str, Any]:
        """
        THE ULTIMATE HEALTH CHECK
        Combines Sentry + Grafana + Chrome DevTools for complete diagnostics

        Args:
            app_label: App to test
            auto_fix: Apply fixes automatically
            visual_testing: Enable visual testing with Chrome DevTools

        Returns:
            Comprehensive health check report
        """
        from datetime import datetime

        print("\n" + "=" * 80)
        print("🚀 ULTIMATE ADMIN HEALTH CHECK")
        print("   Chrome DevTools + Sentry + Grafana + Admin Diagnostics")
        print("=" * 80 + "\n")

        report = {
            "timestamp": datetime.now().isoformat(),
            "app": app_label or "all",
            "auto_fix_enabled": auto_fix,
            "visual_testing_enabled": visual_testing,
            "services": {
                "sentry": self.sentry.is_enabled() if self.sentry else False,
                "grafana": self.grafana.is_enabled() if self.grafana else False,
                "chrome": self.chrome.is_enabled() if self.chrome else False,
            },
        }

        # 1. SCHEMA DIAGNOSTICS
        print("📊 Running schema diagnostics...")
        schema_results = self.diagnose_schema_errors(app_label)
        report["schema"] = schema_results

        # 2. ADMIN URL TESTING
        print("🧪 Testing admin URLs...")
        admin_results = self.test_admin_urls(app_label, auto_fix)
        report["admin"] = admin_results

        # 3. VISUAL TESTING (if Chrome DevTools available)
        if visual_testing and self.chrome:
            print("📸 Running visual tests...")
            visual_results = []

            for tested in admin_results.get("tested", []):
                url = tested["url"]
                print(f"   Testing: {url}")

                chrome_result = self.chrome.test_admin_page(url)
                visual_results.append(chrome_result)

            report["visual"] = visual_results

        # 4. PERFORMANCE ANALYSIS (if Chrome DevTools available)
        if visual_testing and self.chrome:
            print("⚡ Analyzing performance...")
            performance_results = []

            for tested in admin_results.get("tested", [])[:5]:  # Sample first 5
                url = tested["url"]
                perf = self.chrome.measure_performance(url)
                performance_results.append({"url": url, "metrics": perf})

            report["performance"] = performance_results

        # 5. UNUSED TABLES
        print("🗑️  Checking for unused tables...")
        unused_results = self.find_unused_tables()
        report["unused"] = unused_results

        # 6. GRAFANA EXPORT (if available)
        if self.grafana and self.grafana.is_enabled():
            print("📊 Exporting metrics to Grafana...")
            self.grafana.export_admin_diagnostics_metrics(
                {
                    "tested": len(admin_results.get("tested", [])),
                    "errors": len(admin_results.get("errors", [])),
                    "fixed": len(admin_results.get("fixed", [])),
                }
            )

        # 7. SUMMARY
        summary = {
            "schema": {
                "missing_tables": len(schema_results["missing_tables"]),
                "missing_columns": len(schema_results["missing_columns"]),
            },
            "admin": {
                "tested": len(admin_results.get("tested", [])),
                "errors": len(admin_results.get("errors", [])),
                "fixed": len(admin_results.get("fixed", [])),
            },
            "unused": {
                "tables": unused_results["statistics"]["unused_tables"],
                "rows": unused_results["statistics"]["unused_rows"],
            },
            "services_active": sum(1 for v in report["services"].values() if v),
        }

        report["summary"] = summary

        # Print summary
        print("\n" + "=" * 80)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 80)
        print(f"\n  Schema:")
        print(f"    Missing tables: {summary['schema']['missing_tables']}")
        print(f"    Missing columns: {summary['schema']['missing_columns']}")
        print(f"\n  Admin:")
        print(f"    Pages tested: {summary['admin']['tested']}")
        print(f"    Errors found: {summary['admin']['errors']}")
        print(f"    Errors fixed: {summary['admin']['fixed']}")
        print(f"\n  Database:")
        print(f"    Unused tables: {summary['unused']['tables']}")
        print(f"    Unused rows: {summary['unused']['rows']}")
        print(f"\n  Services:")
        print(f"    Active: {summary['services_active']}/3 (Sentry, Grafana, Chrome)")

        # Overall status
        if summary["admin"]["errors"] == 0 and summary["schema"]["missing_tables"] == 0:
            print(f"\n  ✅ Status: ALL CHECKS PASSED!")
        elif summary["admin"]["errors"] > 0:
            print(f"\n  ⚠️  Status: {summary['admin']['errors']} error(s) found")

        print("\n" + "=" * 80 + "\n")

        return report

    # ============================================================================
    # HELPERS
    # ============================================================================

    def _generate_recommendations(self, results: Dict[str, Any]):
        """Generate recommendations based on diagnostics results"""
        recommendations = []

        if results["missing_tables"]:
            recommendations.append(
                {
                    "type": "missing_tables",
                    "count": len(results["missing_tables"]),
                    "action": "Run fix_table_references to auto-create VIEWs",
                }
            )

        if results["missing_columns"]:
            recommendations.append(
                {
                    "type": "missing_columns",
                    "count": len(results["missing_columns"]),
                    "action": "Run fix_all_views to update VIEW definitions",
                }
            )

        results["recommendations"] = recommendations


# Global singleton instance
_admin_diagnostics = None


def get_admin_diagnostics() -> AdminDiagnosticsService:
    """Get or create the global AdminDiagnosticsService instance"""
    global _admin_diagnostics
    if _admin_diagnostics is None:
        _admin_diagnostics = AdminDiagnosticsService()
    return _admin_diagnostics
