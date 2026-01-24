"""
Unified Admin Diagnostics Command
Provides access to all admin diagnostic tools through a single command
"""

import json

from django.core.management.base import BaseCommand

from apps.bfagent.services.admin_diagnostics import get_admin_diagnostics


class Command(BaseCommand):
    help = "Run admin diagnostics and auto-fix tools"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            type=str,
            choices=[
                "diagnose",
                "fix-tables",
                "fix-views",
                "test-admin",
                "find-unused",
                "health-check",
                "ultimate-check",
            ],
            help="Diagnostic action to perform",
        )
        parser.add_argument("--app", type=str, help="App label to focus on (e.g., writing_hub)")
        parser.add_argument(
            "--fix", action="store_true", help="Auto-fix errors (for test-admin and fix-tables)"
        )
        parser.add_argument(
            "--visual",
            action="store_true",
            help="Enable visual testing with Chrome DevTools (for ultimate-check)",
        )
        parser.add_argument("--json", action="store_true", help="Output results as JSON")

    def handle(self, *args, **options):
        action = options["action"]
        app_label = options.get("app")
        auto_fix = options.get("fix", False)
        visual_testing = options.get("visual", False)
        json_output = options.get("json", False)

        service = get_admin_diagnostics()

        # Execute action
        if action == "diagnose":
            results = service.diagnose_schema_errors(app_label)
            self._display_schema_diagnostics(results, json_output)

        elif action == "fix-tables":
            results = service.fix_table_references(dry_run=not auto_fix)
            self._display_fix_results(results, json_output)

        elif action == "fix-views":
            results = service.fix_all_views()
            self._display_view_fixes(results, json_output)

        elif action == "test-admin":
            results = service.test_admin_urls(app_label, auto_fix)
            self._display_admin_tests(results, json_output)

        elif action == "find-unused":
            results = service.find_unused_tables()
            self._display_unused_tables(results, json_output)

        elif action == "health-check":
            results = self._run_health_check(service, app_label, auto_fix)
            self._display_health_check(results, json_output)

        elif action == "ultimate-check":
            results = service.ultimate_health_check(app_label, auto_fix, visual_testing)
            if json_output:
                self.stdout.write(json.dumps(results, indent=2, default=str))

    def _run_health_check(self, service, app_label, auto_fix):
        """Run comprehensive health check"""
        return {
            "schema": service.diagnose_schema_errors(app_label),
            "admin": service.test_admin_urls(app_label, auto_fix),
            "unused": service.find_unused_tables(),
        }

    # ============================================================================
    # DISPLAY METHODS
    # ============================================================================

    def _display_schema_diagnostics(self, results, json_output):
        """Display schema diagnostics results"""
        if json_output:
            self.stdout.write(json.dumps(results, indent=2))
            return

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🔍 SCHEMA DIAGNOSTICS"))
        self.stdout.write("=" * 80 + "\n")

        # Missing tables
        if results["missing_tables"]:
            self.stdout.write(
                self.style.ERROR(f"\n❌ MISSING TABLES ({len(results['missing_tables'])}):")
            )
            for item in results["missing_tables"]:
                self.stdout.write(f"  • {item['model']}")
                self.stdout.write(f"    Table: {item['table']}")
                self.stdout.write(f"    Managed: {item['managed']}\n")
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ No missing tables\n"))

        # Missing columns
        if results["missing_columns"]:
            self.stdout.write(
                self.style.ERROR(f"\n❌ MISSING COLUMNS ({len(results['missing_columns'])}):")
            )
            for item in results["missing_columns"]:
                self.stdout.write(f"  • {item['model']}")
                self.stdout.write(f"    Table.Column: {item['table']}.{item['column']}")
                self.stdout.write(f"    Field: {item['field']} ({item['type']})\n")
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ No missing columns\n"))

        # Recommendations
        if results["recommendations"]:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("💡 RECOMMENDATIONS:"))
            self.stdout.write("=" * 80 + "\n")
            for rec in results["recommendations"]:
                self.stdout.write(f"• {rec['type']}: {rec['count']} issues")
                self.stdout.write(f"  → {rec['action']}\n")

    def _display_fix_results(self, results, json_output):
        """Display table fix results"""
        if json_output:
            self.stdout.write(json.dumps(results, indent=2))
            return

        self.stdout.write("\n" + "=" * 80)
        mode = "DRY-RUN" if results["dry_run"] else "APPLIED"
        self.stdout.write(self.style.SUCCESS(f"🔧 FIX TABLE REFERENCES ({mode})"))
        self.stdout.write("=" * 80 + "\n")

        if results["fixes_applied"]:
            for fix in results["fixes_applied"]:
                icon = "📋" if results["dry_run"] else "✅"
                self.stdout.write(f"{icon} {fix['action']}")
                self.stdout.write(f"   {fix['target']} → {fix['source']}\n")
        else:
            self.stdout.write(self.style.SUCCESS("✅ No fixes needed\n"))

        if results["errors"]:
            self.stdout.write(self.style.ERROR("\n❌ ERRORS:"))
            for error in results["errors"]:
                self.stdout.write(f"  • {error['table']}: {error['error']}\n")

    def _display_view_fixes(self, results, json_output):
        """Display view fix results"""
        if json_output:
            self.stdout.write(json.dumps(results, indent=2))
            return

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🔄 FIX ALL VIEWS"))
        self.stdout.write("=" * 80 + "\n")

        if results["fixed"]:
            for view in results["fixed"]:
                self.stdout.write(self.style.SUCCESS(f"✅ Fixed: {view}"))

        if results["errors"]:
            self.stdout.write(self.style.ERROR("\n❌ ERRORS:"))
            for error in results["errors"]:
                self.stdout.write(f"  • {error['view']}: {error['error']}\n")

    def _display_admin_tests(self, results, json_output):
        """Display admin test results"""
        if json_output:
            self.stdout.write(json.dumps(results, indent=2))
            return

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🧪 ADMIN URL TESTING"))
        self.stdout.write("=" * 80 + "\n")

        # Successful tests
        ok_count = len(results["tested"])
        error_count = len(results["errors"])

        self.stdout.write(f"\n✅ Tested: {ok_count}")
        self.stdout.write(f"❌ Errors: {error_count}\n")

        # Show errors
        if results["errors"]:
            self.stdout.write(self.style.ERROR("\n❌ FAILED TESTS:"))
            for error in results["errors"]:
                self.stdout.write(f"\n  • {error['model']}")
                self.stdout.write(f"    URL: {error['url']}")
                if "error" in error:
                    if isinstance(error["error"], dict):
                        self.stdout.write(f"    Error: {error['error'].get('message', 'Unknown')}")
                    else:
                        self.stdout.write(f"    Error: {error['error']}")

        # Show fixes
        if results.get("fixed"):
            self.stdout.write(self.style.SUCCESS("\n\n🔧 AUTO-FIXES APPLIED:"))
            for fix in results["fixed"]:
                self.stdout.write(f"  ✅ {fix['model']}: {fix['fix']}\n")

    def _display_unused_tables(self, results, json_output):
        """Display unused tables"""
        if json_output:
            self.stdout.write(json.dumps(results, indent=2))
            return

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🗑️ UNUSED TABLES"))
        self.stdout.write("=" * 80 + "\n")

        stats = results["statistics"]
        self.stdout.write(f"\nTotal tables: {stats['total_tables']}")
        self.stdout.write(f"Used tables: {stats['used_tables']}")
        self.stdout.write(f"Unused tables: {stats['unused_tables']}")
        self.stdout.write(f"Unused rows: {stats['unused_rows']:,}\n")

        if results["unused_tables"]:
            self.stdout.write(self.style.WARNING("\n⚠️  UNUSED TABLES:"))
            for table in sorted(results["unused_tables"], key=lambda x: -x["rows"]):
                self.stdout.write(
                    f"  • {table['name']:40s} " f"({table['type']:5s}) " f"{table['rows']:>8,} rows"
                )

    def _display_health_check(self, results, json_output):
        """Display complete health check"""
        if json_output:
            self.stdout.write(json.dumps(results, indent=2))
            return

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("💊 ADMIN HEALTH CHECK"))
        self.stdout.write("=" * 80 + "\n")

        # Schema
        schema = results["schema"]
        self.stdout.write("\n📊 Schema Status:")
        self.stdout.write(f"  Missing tables: {len(schema['missing_tables'])}")
        self.stdout.write(f"  Missing columns: {len(schema['missing_columns'])}")

        # Admin
        admin = results["admin"]
        self.stdout.write("\n🌐 Admin Status:")
        self.stdout.write(f"  Tested: {len(admin['tested'])}")
        self.stdout.write(f"  Errors: {len(admin['errors'])}")
        if admin.get("fixed"):
            self.stdout.write(f"  Fixed: {len(admin['fixed'])}")

        # Unused
        unused = results["unused"]
        self.stdout.write("\n🗑️  Database Cleanup:")
        self.stdout.write(f"  Unused tables: {unused['statistics']['unused_tables']}")
        self.stdout.write(f"  Unused rows: {unused['statistics']['unused_rows']:,}")

        # Overall status
        total_issues = (
            len(schema["missing_tables"]) + len(schema["missing_columns"]) + len(admin["errors"])
        )

        self.stdout.write("\n" + "=" * 80)
        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS("✅ ALL CHECKS PASSED!"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ {total_issues} ISSUES FOUND"))
            self.stdout.write("\nRun with --fix to auto-fix issues")
        self.stdout.write("=" * 80 + "\n")
