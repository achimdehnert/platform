# Migration Scripts Documentation

## 🛠️ Available Tools

### 1. auto_fix_migrations.py ⭐ PRIMARY TOOL

**Purpose:** Automatically fix common migration issues

**Features:**
- Removes auto-generated initial migrations (0025-0030)
- Fixes operations on non-existent models
- Cleans up unused imports
- Detects syntax errors

**Usage:**
```bash
python scripts/auto_fix_migrations.py

# OR via Makefile
make migrate-safe  # Calls it automatically
```

**Output:**
```
🔧 Auto-Fix Migrations
============================================================

Step 1: Removing auto-generated initial migrations...
   ✅ Removed: 0025_initial.py

Step 2: Checking and fixing migration files...
   ✅ 0021_agenttype_and_more.py: Operations cleaned successfully
   ✅ 0022_agenttype_...py: Operations cleaned successfully

============================================================
✅ Auto-fixed 2 migration file(s)

💡 Next: Run 'make migrate-safe' to apply migrations
```

### 2. validate_migrations.py

**Purpose:** Validate migration files for issues

**Features:**
- Checks database state
- Validates migration file syntax
- Detects problematic operations
- Reports issues without fixing

**Usage:**
```bash
python scripts/validate_migrations.py
```

### 3. clean_all_migrations.py

**Purpose:** Comprehensive migration cleaner

**Features:**
- Identifies all operations on removed models
- Creates backups before changes
- Removes problematic operations
- Reports success/failure

**Usage:**
```bash
python scripts/clean_all_migrations.py
```

### 4. fix_broken_migrations.py

**Purpose:** Fix migrations with partial commenting

**Features:**
- Detects REMOVED comments with leftover code
- Replaces broken operations blocks
- Creates backups (.broken_backup)

**Usage:**
```bash
python scripts/fix_broken_migrations.py
```

### 5. check_action_templates.py

**Purpose:** Verify ActionTemplate table exists

**Features:**
- Checks for action_templates table
- Shows record count
- Quick verification tool

**Usage:**
```bash
python scripts/check_action_templates.py
```

**Output:**
```
✅ action_templates table EXISTS!
   Records: 0
```

## 🎯 When to Use Each Tool

### Daily Development
```bash
make migrate-safe  # Uses auto_fix_migrations.py
```

### Debugging
```bash
python scripts/validate_migrations.py  # Check issues
python scripts/auto_fix_migrations.py  # Fix issues
```

### Major Cleanup
```bash
python scripts/clean_all_migrations.py  # Nuclear option
```

### Verification
```bash
python scripts/check_action_templates.py  # Verify tables
```

## 🔧 Configuration

### Removed Models List

All scripts reference this list:
```python
REMOVED_MODELS = {
    'agents', 'bookprojects', 'booktypes', 'llms', 
    'agentexecutions', 'agentartifacts', 'characters', 'bookchapters',
    'enrichmentresponse', 'agentaction'
}
```

**Why removed?** Tables exist in DB but not in migration state.

### Backup Conventions

- `.backup` - Standard backup
- `.broken_backup` - Before syntax fix
- `.pre_clean_backup` - Before operations cleanup

## 📊 Tool Comparison

| Feature | auto_fix | validate | clean_all | fix_broken |
|---------|----------|----------|-----------|------------|
| Remove 0025+ | ✅ | ❌ | ❌ | ❌ |
| Fix syntax | ⚠️ Detect | ⚠️ Detect | ❌ | ✅ |
| Clean operations | ✅ | ❌ | ✅ | ❌ |
| Clean imports | ✅ | ❌ | ✅ | ❌ |
| Create backups | ❌ | ❌ | ✅ | ✅ |
| Reports only | ❌ | ✅ | ❌ | ❌ |

**Recommendation:** Use `auto_fix_migrations.py` as primary tool.

## 🚨 Common Scenarios

### Scenario 1: Django creates 0025_initial.py

```bash
# Problem: Django keeps creating new initial migration
# Solution:
make migrate-safe  # Auto-removes it
```

### Scenario 2: Syntax error in migration

```bash
# Problem: SyntaxError: closing parenthesis ')' does not match
# Solution:
python scripts/fix_broken_migrations.py  # Fixes syntax
make migrate-safe  # Validates and applies
```

### Scenario 3: KeyError for model

```bash
# Problem: KeyError: ('bfagent', 'modelname')
# Solution:
python scripts/auto_fix_migrations.py  # Removes operations
make migrate-safe  # Applies clean migrations
```

### Scenario 4: Migration state unclear

```bash
# Check what's wrong:
python scripts/validate_migrations.py

# Fix issues:
python scripts/auto_fix_migrations.py

# Verify:
make migrate-check
```

## 💡 Best Practices

### DO ✅
- Run via Makefile when possible (`make migrate-safe`)
- Let `auto_fix_migrations.py` handle common issues
- Check output for reported issues
- Keep database backups

### DON'T ❌
- Run multiple tools simultaneously
- Delete backups immediately
- Ignore error messages
- Mix manual edits with auto-fix

## 🔄 Script Workflow

```
User runs: make migrate-safe
           ↓
    auto_fix_migrations.py
           ↓
    1. Remove 0025+ files
    2. Clean operations
    3. Fix imports
           ↓
    validate_migrations.py
           ↓
    Django makemigrations
           ↓
    Remove new 0025+ files
           ↓
    Django migrate
           ↓
    Success or Rollback
```

## 📚 Implementation Details

### auto_fix_migrations.py

**Key Functions:**
- `remove_auto_generated_initial()` - Deletes 0025-0030 files
- `check_migration_syntax()` - Validates Python syntax
- `has_problematic_operations()` - Detects removed model refs
- `clean_migration_operations()` - Removes bad operations

**Algorithm:**
1. Scan migrations directory
2. Delete 0025-0030 files
3. For each 0002-0024:
   - Check syntax
   - Check for REMOVED_MODELS references
   - Replace operations block if needed
   - Clean imports
4. Report results

### validate_migrations.py

**Key Functions:**
- `get_database_tables()` - Lists DB tables
- `get_database_indexes()` - Lists DB indexes
- `validate_migration_file()` - Checks file validity

**Algorithm:**
1. Connect to database
2. Get table/index lists
3. For each migration:
   - Check file exists
   - Validate syntax
   - Check operations
4. Report status

## 🎓 Advanced Usage

### Custom Model List

Edit `auto_fix_migrations.py`:
```python
REMOVED_MODELS = {
    'agents', 'bookprojects',  # Add/remove as needed
    # ... your models ...
}
```

### Dry Run Mode

Currently not supported. Consider adding:
```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    # ... use args.dry_run ...
```

### Verbose Output

Add `--verbose` flag for detailed logging (future enhancement).

## 🆘 Troubleshooting

### Script won't run

```bash
# Check Python version
python --version  # Should be 3.11+

# Check file exists
ls scripts/auto_fix_migrations.py

# Check permissions (Unix)
chmod +x scripts/auto_fix_migrations.py
```

### No issues found but migrations fail

```bash
# Manual cleanup
make migrate-clean

# Try again
make migrate-safe

# If still fails, check database
python scripts/check_action_templates.py
```

### Backup files accumulate

```bash
# Clean old backups
make migrate-clean

# Or manually
rm apps/bfagent/migrations/*.backup
```

## 📞 Support

### Debug Commands

```bash
# Show migration status
make migrate-status

# Show file count
ls apps/bfagent/migrations/00*.py | wc -l

# Check for initial files
ls apps/bfagent/migrations/*initial*.py
```

### Log Files

Scripts output to stdout only. Redirect if needed:
```bash
python scripts/auto_fix_migrations.py > migration_fix.log 2>&1
```

---

**Last Updated:** 2025-10-14  
**Maintainer:** Development Team  
**Version:** 2.0 (Auto-Fix Era)
