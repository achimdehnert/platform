# Helper Scripts

## Purpose
One-time helper scripts for setup, cleanup, initialization, and testing.

## Usage Guidelines

### ✅ Scripts belong here if they:
- Are used for **one-time setup** or initialization
- Are **cleanup** or **maintenance** tasks
- Are for **testing** or **demo data** creation
- Are **temporary fixes** for specific issues
- Are **experimental** or **proof-of-concept** code

### ❌ Scripts should be in `scripts/tools/` if they:
- Are used **regularly** in development workflow
- Are part of **CI/CD pipeline**
- Are **production tools** (formatters, scanners, validators)
- Are **enterprise-grade** tools with ongoing maintenance

## Categories

### Cleanup Scripts
- `cleanup_*.py` - Database cleanup, duplicate removal, etc.

### Initialization Scripts  
- `init_*.py` - One-time database initialization
- `setup_*.py` - Environment setup, demo data creation

### Fix Scripts
- `fix_*.py` - One-time bug fixes, migration repairs

### Testing Scripts
- `create_*.py` - Test data generators
- `demo_*.py` - Demo environment setup

## Moving Scripts

When moving a management command to helpers:

1. **Copy** the script here
2. **Update imports** if necessary (Django settings path)
3. **Add to .gitignore** if contains sensitive data
4. **Document** in this README
5. **Remove** from `management/commands/` after verification

## Running Helper Scripts

```bash
# From project root
python scripts/helpers/script_name.py

# Or with Django environment
python manage.py shell < scripts/helpers/script_name.py
```

## Archiving

When a script is no longer needed:
1. Move to `scripts/archive/`
2. Document reason in git commit
3. Update this README with archived date
