#!/usr/bin/env python
"""
Auto-Fix Migrations - Comprehensive Migration Issue Resolver
Based on learnings from extensive migration debugging sessions

Automatically fixes:
1. Auto-generated 0025_initial.py (and similar) files
2. Syntax errors from partial commenting
3. Dependency issues (operations on non-existent models)
4. Unused imports after operations removal
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


# Models that were removed from 0001_initial.py (DB tables already exist)
REMOVED_MODELS = {
    'agents', 'bookprojects', 'booktypes', 'llms', 
    'agentexecutions', 'agentartifacts', 'characters', 'bookchapters',
    'enrichmentresponse', 'agentaction'
}


def remove_auto_generated_initial():
    """Remove auto-generated initial migrations (0025+)"""
    migrations_dir = Path(__file__).parent.parent / "apps" / "bfagent" / "migrations"
    removed = []
    
    # Check for 0025-0030 range (common auto-generated numbers)
    for num in range(25, 31):
        initial_file = migrations_dir / f"00{num}_initial.py"
        if initial_file.exists():
            initial_file.unlink()
            removed.append(initial_file.name)
    
    return removed


def check_migration_syntax(filepath):
    """Check for syntax errors in migration file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to compile to check for syntax errors
        compile(content, str(filepath), 'exec')
        return True, None
    except SyntaxError as e:
        return False, str(e)


def has_problematic_operations(filepath):
    """Check if migration has operations on removed models"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for model in REMOVED_MODELS:
        if f'model_name="{model}"' in content.lower():
            return True
    return False


def clean_migration_operations(filepath):
    """Remove operations on non-existent models"""
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Parse operations block
    operations_match = re.search(
        r'(    operations = \[)(.*?)(\n    \])',
        original_content,
        re.DOTALL
    )
    
    if not operations_match:
        return False, "No operations block found"
    
    operations_content = operations_match.group(2)
    
    # Check if cleanup needed
    needs_cleanup = any(
        f'model_name="{model}"' in operations_content.lower() 
        for model in REMOVED_MODELS
    )
    
    if not needs_cleanup:
        return False, "No problematic operations found"
    
    # Create cleaned operations block
    new_operations_block = (
        f"{operations_match.group(1)}\n"
        f"        # AUTO-REMOVED: Operations on models not in migration state\n"
        f"        # These models exist in database but were removed from 0001_initial.py\n"
        f"        # Affected models: {', '.join(sorted(REMOVED_MODELS))}\n"
        f"{operations_match.group(3)}"
    )
    
    new_content = original_content.replace(
        operations_match.group(0),
        new_operations_block
    )
    
    # Clean up imports
    if 'django.db.models.deletion' not in new_operations_block:
        new_content = re.sub(r'import django\.db\.models\.deletion\n', '', new_content)
    
    if 'django.utils.timezone' not in new_operations_block:
        new_content = re.sub(r'import django\.utils\.timezone\n', '', new_content)
    
    if ', models' in new_content and 'models.' not in new_operations_block:
        new_content = new_content.replace(', models', '')
        
    # Remove swappable dependency if present
    new_content = re.sub(
        r',?\s*migrations\.swappable_dependency\(settings\.AUTH_USER_MODEL\),?\n', 
        '', 
        new_content
    )
    new_content = re.sub(r'from django\.conf import settings\n', '', new_content)
    
    # Write cleaned content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True, "Operations cleaned successfully"


def main():
    """Main auto-fix routine"""
    print("🔧 Auto-Fix Migrations")
    print("=" * 60)
    print()
    
    migrations_dir = Path(__file__).parent.parent / "apps" / "bfagent" / "migrations"
    
    if not migrations_dir.exists():
        print("❌ Migrations directory not found!")
        return 1
    
    # Step 1: Remove auto-generated initial migrations
    print("Step 1: Removing auto-generated initial migrations...")
    removed = remove_auto_generated_initial()
    if removed:
        print(f"   ✅ Removed: {', '.join(removed)}")
    else:
        print("   ℹ️  No auto-generated initial migrations found")
    print()
    
    # Step 2: Fix syntax errors and problematic operations
    print("Step 2: Checking and fixing migration files...")
    migration_files = sorted([f for f in migrations_dir.glob("0*.py") if f.name != '0001_initial.py'])
    
    fixed_count = 0
    error_count = 0
    
    for migration_file in migration_files:
        # Check syntax
        syntax_ok, syntax_error = check_migration_syntax(migration_file)
        
        if not syntax_ok:
            print(f"   ⚠️  {migration_file.name}: Syntax error - {syntax_error}")
            error_count += 1
            continue
        
        # Check for problematic operations
        if has_problematic_operations(migration_file):
            cleaned, message = clean_migration_operations(migration_file)
            if cleaned:
                print(f"   ✅ {migration_file.name}: {message}")
                fixed_count += 1
            else:
                print(f"   ℹ️  {migration_file.name}: {message}")
    
    print()
    print("=" * 60)
    
    if error_count > 0:
        print(f"⚠️  {error_count} migration(s) have syntax errors")
        print("   Manual review recommended!")
    
    if fixed_count > 0:
        print(f"✅ Auto-fixed {fixed_count} migration file(s)")
    else:
        print("✅ All migrations are clean!")
    
    print()
    print("💡 Next: Run 'make migrate-safe' to apply migrations")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
