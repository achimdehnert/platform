#!/usr/bin/env python
"""
Comprehensive Migration Cleaner
Systematically removes all operations on models that don't exist in migration state
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


# Models that were removed from 0001_initial.py
REMOVED_MODELS = {
    'agents', 'bookprojects', 'booktypes', 'llms', 
    'agentexecutions', 'agentartifacts', 'characters', 'bookchapters',
    'enrichmentresponse', 'agentaction'  # Added based on errors
}


def clean_migration_file(filepath):
    """
    Clean a migration file by removing all operations on non-existent models
    """
    print(f"🔧 Processing: {filepath.name}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Backup
    backup_path = filepath.with_suffix('.py.pre_clean_backup')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original_content)
    
    # Parse migration to find operations block
    operations_match = re.search(
        r'(    operations = \[)(.*?)(\n    \])',
        original_content,
        re.DOTALL
    )
    
    if not operations_match:
        print(f"   ⚠️ No operations block found - skipping")
        backup_path.unlink()
        return False
    
    operations_content = operations_match.group(2)
    
    # Check if operations involve removed models
    needs_cleaning = False
    for model in REMOVED_MODELS:
        if f'model_name="{model}"' in operations_content.lower():
            needs_cleaning = True
            break
    
    if not needs_cleaning:
        print(f"   ✅ No operations on removed models - skipping")
        backup_path.unlink()
        return False
    
    # Extract individual operations
    operations_list = []
    current_op = []
    paren_depth = 0
    in_operation = False
    
    for line in operations_content.split('\n'):
        stripped = line.strip()
        
        # Start of an operation
        if stripped.startswith('migrations.'):
            in_operation = True
            current_op = [line]
            paren_depth = line.count('(') - line.count(')')
        elif in_operation:
            current_op.append(line)
            paren_depth += line.count('(') - line.count(')')
            
            # End of operation
            if paren_depth == 0 and stripped.endswith('),'):
                operations_list.append('\n'.join(current_op))
                current_op = []
                in_operation = False
        elif stripped.startswith('#'):
            # Keep comments
            if not in_operation:
                operations_list.append(line)
    
    # Filter out operations on removed models
    cleaned_operations = []
    removed_count = 0
    
    for op in operations_list:
        # Check if this operation references a removed model
        has_removed_model = False
        for model in REMOVED_MODELS:
            if f'model_name="{model}"' in op.lower():
                has_removed_model = True
                removed_count += 1
                break
        
        if not has_removed_model and not op.strip().startswith('#'):
            cleaned_operations.append(op)
        elif op.strip().startswith('#'):
            # Keep existing comments
            cleaned_operations.append(op)
    
    if removed_count == 0:
        print(f"   ✅ No operations removed")
        backup_path.unlink()
        return False
    
    # Build new operations block
    if cleaned_operations:
        # Filter empty lines
        cleaned_ops_text = '\n'.join([op for op in cleaned_operations if op.strip()])
    else:
        cleaned_ops_text = f"""
        # REMOVED: All operations on models not in migration state
        # These models were created in earlier migrations or already exist in the database
        # Total operations removed: {removed_count}"""
    
    new_operations_block = (
        f"{operations_match.group(1)}"
        f"{cleaned_ops_text}\n"
        f"{operations_match.group(3)}"
    )
    
    new_content = original_content.replace(
        operations_match.group(0),
        new_operations_block
    )
    
    # Clean up imports if no operations remain
    if not cleaned_operations or all(op.strip().startswith('#') for op in cleaned_operations):
        # Remove unused imports
        new_content = re.sub(r'import django\.db\.models\.deletion\n', '', new_content)
        new_content = re.sub(r'import django\.utils\.timezone\n', '', new_content)
        new_content = re.sub(r'from django\.conf import settings\n', '', new_content)
        new_content = re.sub(r'from django\.db import migrations, models\n', 
                            'from django.db import migrations\n', new_content)
        # Remove swappable dependency if present
        new_content = re.sub(r',?\s*migrations\.swappable_dependency\(settings\.AUTH_USER_MODEL\),?\n', 
                            '', new_content)
    
    # Write cleaned content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"   ✅ Cleaned! Removed {removed_count} operations on non-existent models")
    print(f"   📦 Backup: {backup_path.name}")
    return True


def main():
    """Main cleaning routine"""
    print("🧹 Comprehensive Migration Cleaner")
    print("=" * 60)
    print()
    print(f"🎯 Target: Operations on models removed from 0001_initial.py")
    print(f"📋 Removed models: {', '.join(sorted(REMOVED_MODELS))}")
    print()
    
    # Find all migration files (skip 0001)
    migrations_dir = Path(__file__).parent.parent / "apps" / "bfagent" / "migrations"
    migration_files = sorted([f for f in migrations_dir.glob("0*.py") if f.name != '0001_initial.py'])
    
    print(f"📁 Found {len(migration_files)} migration files to process")
    print()
    
    cleaned_count = 0
    
    for migration_file in migration_files:
        if clean_migration_file(migration_file):
            cleaned_count += 1
        print()
    
    if cleaned_count > 0:
        print("=" * 60)
        print(f"✅ Successfully cleaned {cleaned_count} migration file(s)")
        print("📦 Backups created with .pre_clean_backup extension")
        print()
        print("💡 Next steps:")
        print("   1. Review the changes")
        print("   2. Run: make migrate-safe")
        print("   3. If successful, delete backup files")
    else:
        print("=" * 60)
        print("✅ All migrations are already clean!")
        print("   No operations on removed models found")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
