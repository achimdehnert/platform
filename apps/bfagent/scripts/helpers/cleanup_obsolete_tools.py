#!/usr/bin/env python
"""
Tool Cleanup Script - Remove obsolete and duplicate tools
Based on TOOL_AUDIT_2025.md analysis

SAFE: Creates backup before deletion
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

# Root directory
SCRIPTS_DIR = Path(__file__).parent

# Backup directory
BACKUP_DIR = (
    SCRIPTS_DIR.parent / ".tool_backups" / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)


# ============================================================================
# DELETE LISTS
# ============================================================================

TO_DELETE = {
    "OLD_VERSIONS": [
        "consistency-framework-v4.py",
        "consistency_framework - Kopie.py",
        "consistency_framework_v2_backup.py",
    ],
    "HTMX_DUPLICATES": [
        "htmx_conformity_scanner.py",
        "analyze_htmx_issues.py",
        "htmx_debug_helper.py",
        "fix_htmx_critical.py",
        "test_htmx_middleware_phase1.py",
    ],
    "QUALITY_DUPLICATES": [
        "code_repair_tool.py",
        "quality_gate_fixer.py",
        "quick_quality_check.py",
        "safe_auto_fixer.py",
        "targeted_quality_fixer.py",
        "autofix_recovery_tool.py",
    ],
    "ANALYZER_DUPLICATES": [
        "enhanced_cli_analyzer.py",
        "enhanced_tool_analyzer.py",
        "enhanced_unicode_analyzer.py",
        "hybrid_analyzer.py",
        "integrated_analyzer.py",
        "optimized_hybrid_analyzer.py",
        "optimized_hybrid_analyzer_backup.py",
        "unicode_safe_analyzer.py",
    ],
    "THEME_DUPLICATES": [
        "optimized-css-theme-switcher.py",  # Keep css_theme_switcher.py
        "theme_switcher_simple.py",
        "fix_theme_css.py",
    ],
    "GRAPHQL_TOOLS": [
        "django_graphql_monitoring.py",
        "graphql_monitor_setup.py",
        "graphql_resource_analyzer.py",
        "graphql_schema_generator.py",
    ],
    "ONE_TIME_FIXES": [
        "fix_corrupted_urls.py",
        "fix_template_corruption.py",
    ],
    "SCHEMA_CHECKERS": [
        "check_bookprojects_schema.py",
        "check_chapter_fields.py",
        "check_character_description.py",
        "check_main_content.py",
        "check_world_system.py",
    ],
    "DEBUG_SCRIPTS": [
        "test_worlds_generation.py",
        "debug_project_form.py",
        "tool_integration_optimizer.py",
    ],
}


# ============================================================================
# BACKUP & DELETE
# ============================================================================


def create_backup():
    """Create backup directory"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ Backup directory created: {BACKUP_DIR}")


def backup_and_delete(category, files):
    """Backup files and delete from scripts directory"""
    print(f"\n{'='*80}")
    print(f"📦 Processing: {category}")
    print(f"{'='*80}")

    category_backup = BACKUP_DIR / category.lower()
    category_backup.mkdir(exist_ok=True)

    deleted_count = 0
    missing_count = 0

    for filename in files:
        source = SCRIPTS_DIR / filename

        if source.exists():
            # Backup
            dest = category_backup / filename
            shutil.copy2(source, dest)

            # Delete
            source.unlink()

            print(f"  ✅ Deleted: {filename}")
            deleted_count += 1
        else:
            print(f"  ⚠️  Not found: {filename}")
            missing_count += 1

    print(f"\n  📊 Category Summary:")
    print(f"     - Deleted: {deleted_count}")
    print(f"     - Not found: {missing_count}")
    print(f"     - Total: {len(files)}")


def generate_summary():
    """Generate cleanup summary"""
    total_deleted = 0
    total_missing = 0

    for category, files in TO_DELETE.items():
        existing = sum(1 for f in files if (SCRIPTS_DIR / f).exists())
        total_deleted += existing
        total_missing += len(files) - existing

    return total_deleted, total_missing


# ============================================================================
# MAIN
# ============================================================================


def main():
    print("\n" + "=" * 80)
    print("🧹 BF AGENT TOOL CLEANUP")
    print("=" * 80)

    # Pre-check
    total_to_delete, total_missing = generate_summary()

    print(f"\n📊 PRE-CLEANUP ANALYSIS:")
    print(f"   - Files to delete: {total_to_delete}")
    print(f"   - Already missing: {total_missing}")
    print(f"   - Total in list: {sum(len(files) for files in TO_DELETE.values())}")

    # Confirm
    print(f"\n⚠️  This will DELETE {total_to_delete} files!")
    print(f"   Backup will be created at: {BACKUP_DIR}")
    response = input("\n   Continue? (yes/no): ").strip().lower()

    if response != "yes":
        print("\n❌ Cleanup cancelled.")
        return

    # Create backup
    create_backup()

    # Process deletions
    for category, files in TO_DELETE.items():
        backup_and_delete(category, files)

    # Final summary
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETE")
    print("=" * 80)
    print(f"\n📊 FINAL SUMMARY:")
    print(f"   - Files deleted: {total_to_delete}")
    print(f"   - Backup location: {BACKUP_DIR}")
    print(f"\n📝 NEXT STEPS:")
    print(f"   1. Review remaining tools in scripts/")
    print(f"   2. Update Makefile references")
    print(f"   3. Update Control Center registry")
    print(f"   4. Run: make test (verify nothing broke)")
    print(f"\n💡 To restore: Copy files from {BACKUP_DIR}")


if __name__ == "__main__":
    main()
