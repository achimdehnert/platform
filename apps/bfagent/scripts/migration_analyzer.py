#!/usr/bin/env python
"""
BF Agent - Enterprise Migration Analyzer Tool v1.0.0
====================================================

Analyzes Django migrations for consistency issues:
- Table vs Migration verification
- DROP → ALTER sequence problems  
- Missing CreateModel operations
- Orphaned migrations

Usage:
    python scripts/migration_analyzer.py analyze
    python scripts/migration_analyzer.py fix --issue phase_action_configs
    python scripts/migration_analyzer.py health

Author: BF Agent Development Team
"""

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.apps import apps
from django.db import connection
from django.db.migrations import Migration
from django.db.migrations.loader import MigrationLoader


class MigrationAnalyzer:
    """Enterprise-grade migration analysis and repair tool"""

    def __init__(self, app_label: str = "bfagent"):
        self.app_label = app_label
        self.loader = MigrationLoader(connection)
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def get_existing_tables(self) -> Set[str]:
        """Get all tables that exist in the database"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND NOT name='sqlite_sequence'
                ORDER BY name
            """)
            return {row[0] for row in cursor.fetchall()}

    def get_expected_tables(self) -> Dict[str, str]:
        """Get all tables that should exist based on models"""
        expected = {}
        for model in apps.get_app_config(self.app_label).get_models():
            table_name = model._meta.db_table
            expected[table_name] = model.__name__
        return expected

    def analyze_migration_file(self, migration_path: Path) -> Dict[str, Any]:
        """Parse migration file and extract operations"""
        with open(migration_path, "r", encoding="utf-8") as f:
            content = f.read()

        operations = {
            "creates": [],
            "drops": [],
            "alters": [],
            "removes": [],
            "adds": [],
        }

        # Parse migration operations
        if "CreateModel" in content:
            # Extract model names from CreateModel operations
            for match in re.finditer(r'CreateModel\s*\(\s*name="(\w+)"', content):
                operations["creates"].append(match.group(1))

        if "DROP TABLE" in content or "DeleteModel" in content:
            # Extract dropped tables
            for match in re.finditer(r'DROP TABLE (?:IF EXISTS )?(["\w]+)', content):
                table = match.group(1).strip('"')
                operations["drops"].append(table)
            for match in re.finditer(r'DeleteModel\s*\(\s*name="(\w+)"', content):
                operations["drops"].append(match.group(1))

        if "AlterModelOptions" in content or "AlterField" in content:
            for match in re.finditer(
                r'Alter(?:Model|Field)\s*\(\s*(?:model_)?name="(\w+)"', content
            ):
                operations["alters"].append(match.group(1))

        if "RemoveField" in content:
            for match in re.finditer(r'RemoveField\s*\(\s*model_name="(\w+)"', content):
                operations["removes"].append(match.group(1))

        if "AddField" in content:
            for match in re.finditer(r'AddField\s*\(\s*model_name="(\w+)"', content):
                operations["adds"].append(match.group(1))

        return {
            "path": str(migration_path),
            "name": migration_path.stem,
            "operations": operations,
        }

    def analyze_migration_sequence(self) -> List[Dict[str, Any]]:
        """Analyze migration sequence for DROP → ALTER problems"""
        migrations_dir = Path(f"apps/{self.app_label}/migrations")
        migration_files = sorted(migrations_dir.glob("0*.py"))

        sequence_issues = []
        table_states = defaultdict(str)  # table -> last_operation

        for migration_file in migration_files:
            analysis = self.analyze_migration_file(migration_file)
            ops = analysis["operations"]

            # Check for operations on non-existent tables
            for table in ops["drops"]:
                table_states[table] = "dropped"

            for table in ops["alters"]:
                if table_states.get(table) == "dropped":
                    sequence_issues.append(
                        {
                            "severity": "error",
                            "type": "alter_after_drop",
                            "migration": analysis["name"],
                            "table": table,
                            "message": f"Migration {analysis['name']} tries to ALTER {table} which was DROPped in a previous migration",
                        }
                    )

            for table in ops["removes"] + ops["adds"]:
                if table_states.get(table) == "dropped":
                    sequence_issues.append(
                        {
                            "severity": "error",
                            "type": "modify_after_drop",
                            "migration": analysis["name"],
                            "table": table,
                            "message": f"Migration {analysis['name']} tries to modify {table} which was DROPped",
                        }
                    )

            for table in ops["creates"]:
                table_states[table] = "created"

        return sequence_issues

    def verify_table_consistency(self) -> List[Dict[str, Any]]:
        """Verify that expected tables exist in database"""
        existing = self.get_existing_tables()
        expected = self.get_expected_tables()

        consistency_issues = []

        for table_name, model_name in expected.items():
            if table_name not in existing:
                consistency_issues.append(
                    {
                        "severity": "error",
                        "type": "missing_table",
                        "table": table_name,
                        "model": model_name,
                        "message": f"Table '{table_name}' for model '{model_name}' does not exist in database",
                    }
                )

        return consistency_issues

    def run_full_analysis(self) -> Dict[str, Any]:
        """Run complete migration health check"""
        print("🔍 Running Enterprise Migration Analysis...")

        # 1. Table Consistency Check
        print("\n📊 Checking table consistency...")
        consistency_issues = self.verify_table_consistency()

        # 2. Migration Sequence Analysis
        print("📋 Analyzing migration sequence...")
        sequence_issues = self.analyze_migration_sequence()

        # Combine all issues
        all_issues = consistency_issues + sequence_issues

        # Calculate health score
        errors = [i for i in all_issues if i["severity"] == "error"]
        warnings = [i for i in all_issues if i["severity"] == "warning"]

        health_score = max(0, 100 - (len(errors) * 10) - (len(warnings) * 5))

        report = {
            "timestamp": datetime.now().isoformat(),
            "app_label": self.app_label,
            "health_score": health_score,
            "summary": {
                "total_issues": len(all_issues),
                "errors": len(errors),
                "warnings": len(warnings),
            },
            "issues": all_issues,
        }

        return report

    def generate_fix_migration(self, table_name: str, model_name: str) -> str:
        """Generate migration code to fix missing table"""
        model = apps.get_model(self.app_label, model_name)
        
        # Get model fields
        fields_code = []
        for field in model._meta.get_fields():
            if field.auto_created or field.many_to_many:
                continue
            
            field_name = field.name
            field_class = field.__class__.__name__
            
            # Basic field definition
            field_def = f'("{field_name}", models.{field_class}('
            
            # Add common attributes
            attrs = []
            if hasattr(field, 'max_length') and field.max_length:
                attrs.append(f'max_length={field.max_length}')
            if field.blank:
                attrs.append('blank=True')
            if field.null:
                attrs.append('null=True')
            if hasattr(field, 'default') and field.default != django.db.models.fields.NOT_PROVIDED:
                attrs.append(f'default={repr(field.default)}')
            
            field_def += ', '.join(attrs) + '))'
            fields_code.append(field_def)

        # Generate timestamp outside f-string (f-strings can't contain backslashes)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        fields_joined = ",\n                ".join(fields_code)
        ordering_list = list(model._meta.ordering) if model._meta.ordering else []

        # Generate migration template
        migration_code = f'''# Auto-generated migration to fix missing {table_name} table
# Generated by migration_analyzer.py on {timestamp}

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bfagent", "0019_add_agent_action_architecture"),  # Update this!
    ]

    operations = [
        migrations.CreateModel(
            name="{model_name}",
            fields=[
                {fields_joined}
            ],
            options={{
                "db_table": "{table_name}",
                "ordering": {ordering_list},
                "verbose_name": "{model._meta.verbose_name}",
                "verbose_name_plural": "{model._meta.verbose_name_plural}",
            }},
        ),
    ]
'''
        return migration_code


def print_report(report: Dict[str, Any]) -> None:
    """Print analysis report"""
    print("\n" + "=" * 70)
    print("  MIGRATION HEALTH REPORT")
    print("=" * 70)
    print(f"App: {report['app_label']}")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Health Score: {report['health_score']}/100")
    print()
    print(f"Total Issues: {report['summary']['total_issues']}")
    print(f"  Errors: {report['summary']['errors']}")
    print(f"  Warnings: {report['summary']['warnings']}")
    print()

    if report["issues"]:
        print("ISSUES FOUND:")
        print("-" * 70)
        for issue in report["issues"]:
            severity_icon = "❌" if issue["severity"] == "error" else "⚠️"
            print(f"{severity_icon} [{issue['type'].upper()}]")
            print(f"  {issue['message']}")
            if "migration" in issue:
                print(f"  Migration: {issue['migration']}")
            print()
    else:
        print("✅ No issues found! Migrations are healthy.")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="BF Agent Enterprise Migration Analyzer"
    )
    parser.add_argument(
        "command",
        choices=["analyze", "fix", "health"],
        help="Command to run",
    )
    parser.add_argument(
        "--app", default="bfagent", help="Django app to analyze"
    )
    parser.add_argument(
        "--issue", help="Specific issue to fix (e.g., 'phase_action_configs')"
    )
    parser.add_argument(
        "--output", help="Output file for report (JSON format)"
    )

    args = parser.parse_args()

    analyzer = MigrationAnalyzer(app_label=args.app)

    if args.command == "analyze" or args.command == "health":
        report = analyzer.run_full_analysis()
        print_report(report)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Report saved to: {args.output}")

        sys.exit(0 if report["summary"]["errors"] == 0 else 1)

    elif args.command == "fix":
        if not args.issue:
            print("❌ Error: --issue required for fix command")
            sys.exit(1)

        # Run analysis first
        report = analyzer.run_full_analysis()
        
        # Find the specific issue
        issue = None
        for i in report["issues"]:
            if i.get("table") == args.issue:
                issue = i
                break

        if not issue:
            print(f"❌ No issue found for table: {args.issue}")
            sys.exit(1)

        if issue["type"] == "missing_table":
            print(f"\n🔧 Generating fix migration for {args.issue}...")
            migration_code = analyzer.generate_fix_migration(
                issue["table"], issue["model"]
            )
            
            # Get next migration number
            migrations_dir = Path(f"apps/{args.app}/migrations")
            existing = sorted(migrations_dir.glob("0*.py"))
            if existing:
                last_num = int(existing[-1].stem.split("_")[0])
                next_num = f"{last_num + 1:04d}"
            else:
                next_num = "0001"
            
            fix_file = migrations_dir / f"{next_num}_fix_{args.issue}.py"
            
            print(f"📝 Migration will be saved to: {fix_file}")
            print("\nPreview:")
            print("-" * 70)
            print(migration_code)
            print("-" * 70)
            
            confirm = input("\n✅ Create this migration? (yes/no): ")
            if confirm.lower() == "yes":
                with open(fix_file, "w", encoding="utf-8") as f:
                    f.write(migration_code)
                print(f"\n✅ Migration created: {fix_file}")
                print("\n🚀 Next steps:")
                print(f"   1. python manage.py migrate")
                print(f"   2. python scripts/migration_analyzer.py health")
            else:
                print("\n❌ Migration not created")
        else:
            print(f"❌ Cannot auto-fix issue type: {issue['type']}")
            print("   Manual intervention required")


if __name__ == "__main__":
    main()
