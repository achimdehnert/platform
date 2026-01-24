#!/usr/bin/env python
"""
Smart Migration Validator
Automatically detects and fixes common Django migration issues
"""

import os
import sys
import re
from pathlib import Path

# UTF-8 fix for Windows
os.environ.setdefault("PYTHONUTF8", "1")
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Django setup
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.db import connection
from django.apps import apps


def get_existing_tables():
    """Get all existing database tables"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        return {row[0] for row in cursor.fetchall()}


def get_existing_indexes():
    """Get all existing database indexes"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' 
            ORDER BY name
        """)
        return {row[0] for row in cursor.fetchall()}


def validate_migration_file(filepath, existing_tables, existing_indexes):
    """
    Validate a single migration file and detect issues
    Returns: (has_issues, issues_list)
    """
    issues = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for CreateModel operations with existing tables
    create_models = re.findall(r'migrations\.CreateModel\(\s*name=["\'](\w+)["\']', content)
    for model_name in create_models:
        # Convert model name to table name
        app_label = "bfagent"  # Adjust if needed
        try:
            model_class = apps.get_model(app_label, model_name)
            table_name = model_class._meta.db_table
            if table_name in existing_tables:
                issues.append(f"❌ CreateModel '{model_name}' - table '{table_name}' already exists")
        except LookupError:
            # Model might not exist in current code, check common patterns
            table_name = model_name.lower() + 's'  # Simple pluralization
            if table_name in existing_tables:
                issues.append(f"❌ CreateModel '{model_name}' - table might already exist as '{table_name}'")
    
    # Check for RemoveIndex operations with non-existing indexes
    remove_indexes = re.findall(r'migrations\.RemoveIndex\([^)]*name=["\']([^"\']+)["\']', content)
    for index_name in remove_indexes:
        if index_name not in existing_indexes:
            issues.append(f"⚠️ RemoveIndex '{index_name}' - index does not exist")
    
    return len(issues) > 0, issues


def auto_fix_migration(filepath, existing_tables, existing_indexes):
    """
    Automatically fix common migration issues
    Creates a backup before modifying
    """
    print(f"🔧 Auto-fixing: {filepath.name}")
    
    # Create backup
    backup_path = filepath.with_suffix('.py.backup')
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original_content)
    print(f"   ✅ Backup created: {backup_path.name}")
    
    # Fix content
    fixed_content = original_content
    changes_made = []
    
    # Pattern 1: Comment out CreateModel for existing tables
    create_models = re.finditer(
        r'(        migrations\.CreateModel\(\s*name=["\'](\w+)["\'],.*?\),\n)',
        fixed_content,
        re.DOTALL
    )
    
    for match in create_models:
        full_block = match.group(1)
        model_name = match.group(2)
        
        # Check if table exists
        app_label = "bfagent"
        try:
            model_class = apps.get_model(app_label, model_name)
            table_name = model_class._meta.db_table
            if table_name in existing_tables:
                # Comment out the CreateModel block
                commented = f"        # REMOVED: CreateModel '{model_name}' (table '{table_name}' already exists)\n"
                fixed_content = fixed_content.replace(full_block, commented)
                changes_made.append(f"Commented out CreateModel '{model_name}'")
        except LookupError:
            pass
    
    # Pattern 2: Comment out RemoveIndex for non-existing indexes
    remove_indexes = re.finditer(
        r'(        migrations\.RemoveIndex\([^)]*name=["\']([^"\']+)["\'][^)]*\),\n)',
        fixed_content
    )
    
    for match in remove_indexes:
        full_line = match.group(1)
        index_name = match.group(2)
        if index_name not in existing_indexes:
            commented = f"        # REMOVED: RemoveIndex '{index_name}' (index does not exist)\n"
            fixed_content = fixed_content.replace(full_line, commented)
            changes_made.append(f"Commented out RemoveIndex '{index_name}'")
    
    # Write fixed content if changes were made
    if changes_made:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"   ✅ Applied {len(changes_made)} fixes:")
        for change in changes_made:
            print(f"      • {change}")
        return True
    else:
        print(f"   ℹ️ No fixes needed")
        # Remove unnecessary backup
        backup_path.unlink()
        return False


def main():
    """Main validation and auto-fix routine"""
    print("🔍 Smart Migration Validator")
    print("=" * 60)
    print()
    
    # Get existing DB state
    print("📊 Analyzing database state...")
    existing_tables = get_existing_tables()
    existing_indexes = get_existing_indexes()
    print(f"   • {len(existing_tables)} tables found")
    print(f"   • {len(existing_indexes)} indexes found")
    print()
    
    # Find all migration files
    migrations_dir = Path(__file__).parent.parent / "apps" / "bfagent" / "migrations"
    migration_files = sorted(migrations_dir.glob("0*.py"))
    
    print(f"📁 Found {len(migration_files)} migration files")
    print()
    
    # Validate each migration
    issues_found = False
    files_with_issues = []
    
    for migration_file in migration_files:
        has_issues, issues = validate_migration_file(
            migration_file, 
            existing_tables, 
            existing_indexes
        )
        
        if has_issues:
            issues_found = True
            files_with_issues.append((migration_file, issues))
    
    if not issues_found:
        print("✅ All migrations validated successfully!")
        return 0
    
    # Report issues
    print("⚠️ Migration Issues Detected:")
    print()
    for filepath, issues in files_with_issues:
        print(f"📄 {filepath.name}:")
        for issue in issues:
            print(f"   {issue}")
        print()
    
    # Auto-fix
    print("🔧 Attempting automatic fixes...")
    print()
    
    fixes_applied = 0
    for filepath, _ in files_with_issues:
        if auto_fix_migration(filepath, existing_tables, existing_indexes):
            fixes_applied += 1
        print()
    
    if fixes_applied > 0:
        print(f"✅ Auto-fixed {fixes_applied} migration file(s)")
        print("   Backups created with .backup extension")
        print()
        print("💡 Please review the changes before committing!")
        return 0
    else:
        print("⚠️ Could not auto-fix all issues")
        print("   Manual intervention may be required")
        return 1


if __name__ == "__main__":
    sys.exit(main())
