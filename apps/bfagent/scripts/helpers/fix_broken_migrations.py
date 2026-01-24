#!/usr/bin/env python
"""
Fix Broken Migrations - Auto-cleanup for partially commented migrations
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


def fix_migration_file(filepath):
    """
    Fix a migration file with partially commented CreateModel operations
    """
    print(f"🔧 Fixing: {filepath.name}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    backup_path = filepath.with_suffix('.py.broken_backup')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"   ✅ Backup: {backup_path.name}")
    
    # Find operations block
    operations_match = re.search(
        r'(    operations = \[)(.*?)(\n    \])',
        content,
        re.DOTALL
    )
    
    if not operations_match:
        print(f"   ⚠️ No operations block found!")
        return False
    
    operations_content = operations_match.group(2)
    
    # Check if it has REMOVED comments with leftover code
    has_removed = '# REMOVED:' in operations_content
    has_leftover_code = re.search(r'# REMOVED:.*?\n\s+\),', operations_content)
    
    if has_removed and has_leftover_code:
        # Replace entire operations block with cleaned version
        cleaned_operations = []
        
        # Extract all REMOVED comments
        removed_comments = re.findall(r'(# REMOVED: [^\n]+)', operations_content)
        
        for comment in removed_comments:
            cleaned_operations.append(f"        {comment}")
        
        if cleaned_operations:
            cleaned_operations.append("        # The CreateModel operations have been removed because tables already exist")
        
        new_operations_block = (
            f"{operations_match.group(1)}\n"
            f"{chr(10).join(cleaned_operations)}\n"
            f"{operations_match.group(3)}"
        )
        
        new_content = content.replace(
            operations_match.group(0),
            new_operations_block
        )
        
        # Clean up unused imports
        # Remove django.db.models.deletion if not used elsewhere
        if 'django.db.models.deletion' not in new_operations_block:
            new_content = re.sub(
                r'import django\.db\.models\.deletion\n',
                '',
                new_content
            )
        
        # Remove django.utils.timezone if not used
        if 'django.utils.timezone' not in new_operations_block:
            new_content = re.sub(
                r'import django\.utils\.timezone\n',
                '',
                new_content
            )
        
        # Remove models from django.db import if not used
        if ', models' in new_content and 'models.' not in new_operations_block:
            new_content = new_content.replace(', models', '')
        
        # Write fixed content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"   ✅ Fixed! Removed {len(removed_comments)} broken CreateModel operations")
        return True
    else:
        print(f"   ℹ️ No fixes needed")
        backup_path.unlink()  # Remove unnecessary backup
        return False


def main():
    """Main fix routine"""
    print("🔧 Broken Migration Auto-Fixer")
    print("=" * 60)
    print()
    
    # Find all migration files
    migrations_dir = Path(__file__).parent.parent / "apps" / "bfagent" / "migrations"
    migration_files = sorted(migrations_dir.glob("0*.py"))
    
    print(f"📁 Found {len(migration_files)} migration files")
    print()
    
    fixed_count = 0
    
    for migration_file in migration_files:
        if fix_migration_file(migration_file):
            fixed_count += 1
        print()
    
    if fixed_count > 0:
        print(f"✅ Fixed {fixed_count} migration file(s)")
        print("   Backups created with .broken_backup extension")
        print()
        print("💡 Run 'make migrate-safe' to apply migrations")
    else:
        print("✅ All migrations are already clean!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
