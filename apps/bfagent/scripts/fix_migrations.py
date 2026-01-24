#!/usr/bin/env python
"""
Enterprise-Grade Django Migration Fix Tool
Professional solution for Django migration issues
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import django
from django.apps import apps
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

# Setup Django
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()


class MigrationFixer:
    """Enterprise-Grade Migration Fix Tool"""

    def __init__(self, quiet=False, dry_run=False):
        """Function description."""
        self.quiet = quiet
        self.dry_run = dry_run
        self.backup_dir = Path("backups/migrations")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def log(self, message, level="INFO"):
        """Logging with levels"""
        if not self.quiet:
            prefix = {
                "INFO": "ℹ️",
                "SUCCESS": "✅",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "DEBUG": "🔍",
            }.get(level, "📋")
            print(f"{prefix} {message}")

    def create_backup(self):
        """Create database backup"""
        db_path = Path("bfagent.db")
        if db_path.exists():
            backup_path = self.backup_dir / f"db_backup_{self.timestamp}.sqlite3"
            if not self.dry_run:
                shutil.copy2(db_path, backup_path)
            self.log(f"Database backup: {backup_path}", "SUCCESS")
            return backup_path
        return None

    def diagnose(self):
        """Comprehensive migration diagnosis"""
        self.log("🔍 DIAGNOSING MIGRATION ISSUES", "INFO")
        self.log("=" * 70)

        issues = []

        # Check unapplied migrations
        try:
            from django.db.migrations.executor import MigrationExecutor

            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

            if plan:
                for migration, backwards in plan:
                    issues.append(
                        {
                            "type": "unapplied_migration",
                            "app": migration.app_label,
                            "migration": migration.name,
                            "message": f"Migration {migration.name} not applied",
                            "fix": f"python manage.py migrate {migration.app_label} {migration.name}",
                        }
                    )
        except Exception as e:
            issues.append(
                {
                    "type": "migration_error",
                    "message": f"Migration plan error: {e}",
                    "fix": "Check migration dependencies",
                }
            )

        # Check for missing tables
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}

            for model in apps.get_models():
                if hasattr(model, "_meta"):
                    table_name = model._meta.db_table
                    if table_name not in existing_tables:
                        issues.append(
                            {
                                "type": "missing_table",
                                "app": model._meta.app_label,
                                "model": model.__name__,
                                "table": table_name,
                                "message": f"Table {table_name} missing for model {model.__name__}",
                                "fix": "Create and run migration",
                            }
                        )
        except Exception as e:
            issues.append({"type": "table_check_error", "message": f"Table check error: {e}"})

        # Report issues
        if issues:
            self.log(f"Found {len(issues)} issues:", "WARNING")
            for i, issue in enumerate(issues, 1):
                self.log(f"\n{i}. {issue.get('type', 'unknown').upper()}")
                self.log(f"   {issue['message']}")
                if "fix" in issue:
                    self.log(f"   Fix: {issue['fix']}")
        else:
            self.log("No migration issues found!", "SUCCESS")

        return issues

    def fix_specific_migration(self, app_name, migration_name, fake=False):
        """Fix specific migration"""
        self.log(f"🔧 Fixing migration: {app_name}.{migration_name}")

        if fake:
            self.log("Marking migration as fake (already applied)")
            if not self.dry_run:
                try:
                    call_command("migrate", app_name, migration_name, fake=True, verbosity=0)
                    self.log("Migration marked as applied", "SUCCESS")
                    return True
                except Exception as e:
                    self.log(f"Failed to fake migration: {e}", "ERROR")
                    return False
        else:
            self.log("Applying migration normally")
            if not self.dry_run:
                try:
                    call_command("migrate", app_name, migration_name, verbosity=0)
                    self.log("Migration applied successfully", "SUCCESS")
                    return True
                except Exception as e:
                    self.log(f"Failed to apply migration: {e}", "ERROR")
                    return False

        return True  # Dry run

    def verify_textfield_fix(self):
        """Verify TextField length fix"""
        self.log("🧪 Verifying TextField fix...")

        try:
            from apps.bfagent.forms import BookProjectForm
            from apps.bfagent.models import BookProjects

            # Get test project
            project = BookProjects.objects.get(pk=16)
            self.log(f"Testing with project: {project.title}")

            # Test with long strings
            test_data = {
                "title": project.title,
                "genre": project.genre or "FICTION",
                "content_rating": project.content_rating or "GENERAL",
                "status": project.status or "draft",
                "target_word_count": project.target_word_count or 50000,
                "current_word_count": project.current_word_count or 0,
                "unique_elements": "A" * 4000,  # Long string
                "genre_settings": "B" * 4000,  # Long string
                "book_type_id": project.book_type_id or "",
            }

            form = BookProjectForm(test_data, instance=project)

            if form.is_valid():
                self.log("Form validation PASSES with long text!", "SUCCESS")
                self.log("TextField fix verified successfully!", "SUCCESS")
                return True
            else:
                self.log("Form still has validation errors:", "ERROR")
                for field, errors in form.errors.items():
                    self.log(f"   • {field}: {errors}")
                return False

        except Exception as e:
            self.log(f"Verification failed: {e}", "ERROR")
            return False

    def create_report(self):
        """Create detailed migration report"""
        report_path = self.backup_dir / f"migration_report_{self.timestamp}.json"

        report = {
            "timestamp": self.timestamp,
            "diagnosis": self.diagnose(),
            "database_info": self.get_database_info(),
            "migration_status": self.get_migration_status(),
        }

        if not self.dry_run:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2, default=str)

        self.log(f"Report saved: {report_path}", "SUCCESS")
        return report

    def get_database_info(self):
        """Get database information"""
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT sqlite_version()")
            sqlite_version = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            return {
                "sqlite_version": sqlite_version,
                "table_count": table_count,
                "database_path": str(Path("bfagent.db").absolute()),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_migration_status(self):
        """Get migration status for all apps"""
        try:
            recorder = MigrationRecorder(connection)
            applied = recorder.applied_migrations()

            status = {}
            for app_config in apps.get_app_configs():
                app_name = app_config.name.split(".")[-1]
                status[app_name] = {
                    "applied_migrations": [m[1] for m in applied if m[0] == app_name],
                    "migration_files": self.get_migration_files(app_name),
                }

            return status
        except Exception as e:
            return {"error": str(e)}

    def validate_migration_chain(self, app_name, auto_fix=False):
        """
        Validate migration chain for gaps and fix dependencies
        
        Detects:
        - Missing migration numbers in sequence
        - Broken dependency chains
        - Incorrect parent references
        
        Auto-fixes broken dependencies to point to last existing migration
        """
        self.log(f"🔗 VALIDATING MIGRATION CHAIN: {app_name}", "INFO")
        self.log("=" * 70)
        
        try:
            migration_dir = Path(f"apps/{app_name}/migrations")
            if not migration_dir.exists():
                self.log(f"Migration directory not found: {migration_dir}", "ERROR")
                return False
            
            # Get all migration files (excluding __init__.py)
            migration_files = sorted([
                f for f in migration_dir.glob("*.py") 
                if not f.name.startswith("__")
            ])
            
            # Extract migration numbers
            migrations = {}
            for file in migration_files:
                # Parse filename like "0028_description.py"
                parts = file.stem.split("_", 1)
                if parts[0].isdigit():
                    num = int(parts[0])
                    migrations[num] = {
                        'file': file,
                        'name': file.stem,
                        'number': num
                    }
            
            if not migrations:
                self.log("No numbered migrations found", "WARNING")
                return True
            
            # Check for gaps in sequence
            min_num = min(migrations.keys())
            max_num = max(migrations.keys())
            expected = set(range(min_num, max_num + 1))
            existing = set(migrations.keys())
            missing = sorted(expected - existing)
            
            if missing:
                self.log(f"⚠️  GAPS FOUND in migration sequence: {missing}", "WARNING")
                self.log(f"   Existing migrations: {sorted(existing)}")
            else:
                self.log(f"✅ Migration sequence complete: {min_num:04d} - {max_num:04d}", "SUCCESS")
            
            # Validate and fix dependencies
            issues_fixed = 0
            for num in sorted(migrations.keys()):
                migration = migrations[num]
                file_path = migration['file']
                
                # Read migration file
                content = file_path.read_text(encoding='utf-8')
                
                # Extract dependencies
                import re
                dep_pattern = r'dependencies = \[\s*\("' + app_name + r'", "(\d+)_[^"]+"\)'
                matches = re.findall(dep_pattern, content)
                
                if matches:
                    dep_num = int(matches[0])
                    
                    # Check if dependency exists
                    if dep_num not in migrations:
                        # Find the last existing migration before this one
                        valid_deps = [n for n in migrations.keys() if n < num]
                        if valid_deps:
                            correct_dep = max(valid_deps)
                            correct_dep_name = migrations[correct_dep]['name']
                            
                            self.log(f"❌ {migration['name']}: References missing 0{dep_num:03d}", "ERROR")
                            self.log(f"   Should reference: 0{correct_dep:03d} ({correct_dep_name})")
                            
                            if auto_fix:
                                # Fix the dependency
                                old_dep_pattern = r'(\("' + app_name + r'", ")(\d+_[^"]+)("\))'
                                new_dep = f'\\g<1>{correct_dep_name}\\g<3>'
                                new_content = re.sub(old_dep_pattern, new_dep, content)
                                
                                if not self.dry_run:
                                    file_path.write_text(new_content, encoding='utf-8')
                                    self.log(f"   ✅ FIXED: Updated dependency to {correct_dep_name}", "SUCCESS")
                                    issues_fixed += 1
                                else:
                                    self.log(f"   🧪 DRY RUN: Would fix dependency", "WARNING")
            
            if issues_fixed > 0:
                self.log(f"\n✅ Fixed {issues_fixed} dependency issue(s)", "SUCCESS")
            elif missing:
                self.log(f"\n⚠️  Found {len(missing)} gap(s) but no broken dependencies", "WARNING")
            else:
                self.log("\n✅ Migration chain is valid!", "SUCCESS")
            
            return len(missing) == 0 and issues_fixed == 0
            
        except Exception as e:
            self.log(f"Error validating chain: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False
    
    def get_migration_files(self, app_name):
        """Get migration files for an app"""
        try:
            migration_dir = Path(f"apps/{app_name}/migrations")
            if migration_dir.exists():
                return [f.stem for f in migration_dir.glob("*.py") if not f.name.startswith("__")]
            return []
        except Exception:
            return []


def main():
    """Main entry point with command line interface"""
    parser = argparse.ArgumentParser(description="Enterprise Django Migration Fix Tool")
    parser.add_argument(
        "command",
        choices=["diagnose", "fix", "specific", "report", "verify", "validate-chain"],
        help="Command to execute",
    )
    parser.add_argument("--app", help="App name for specific operations")
    parser.add_argument("--migration", help="Migration name for specific operations")
    parser.add_argument("--fake", action="store_true", help="Mark migration as fake")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically fix detected issues")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--quiet", action="store_true", help="Reduce output")

    args = parser.parse_args()

    # Change to project directory
    os.chdir(project_root)

    fixer = MigrationFixer(quiet=args.quiet, dry_run=args.dry_run)

    if args.dry_run:
        fixer.log("🧪 DRY RUN MODE - No changes will be made", "WARNING")

    # Create backup for non-read-only operations
    if args.command in ["fix", "specific"] and not args.dry_run:
        fixer.create_backup()

    if args.command == "diagnose":
        fixer.diagnose()

    elif args.command == "fix":
        # Auto-fix current issue
        fixer.log("🚀 Auto-fixing current migration issue...")
        success = fixer.fix_specific_migration("bfagent", "0007_fix_text_fields", fake=True)
        if success:
            fixer.verify_textfield_fix()

    elif args.command == "specific":
        if not args.app or not args.migration:
            fixer.log("--app and --migration required for specific command", "ERROR")
            return
        fixer.fix_specific_migration(args.app, args.migration, fake=args.fake)

    elif args.command == "report":
        fixer.create_report()

    elif args.command == "verify":
        fixer.verify_textfield_fix()
    
    elif args.command == "validate-chain":
        if not args.app:
            fixer.log("--app required for validate-chain command", "ERROR")
            fixer.log("Example: python scripts/fix_migrations.py validate-chain --app bfagent --auto-fix")
            return
        fixer.validate_migration_chain(args.app, auto_fix=args.auto_fix)


if __name__ == "__main__":
    main()
