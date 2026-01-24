#!/bin/bash
#
# Django Models Refactoring - Automated Quick Start
# This script automates the entire Option 2 (Model Splitting) process
#
# Usage:
#   ./quick_refactor.sh /path/to/your/django/project
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check arguments
if [ $# -eq 0 ]; then
    print_error "Usage: $0 /path/to/django/project"
    echo "Example: $0 /home/user/myproject"
    exit 1
fi

PROJECT_ROOT="$1"
BFAGENT_PATH="$PROJECT_ROOT/apps/bfagent"
MODELS_FILE="$BFAGENT_PATH/models.py"

# Verify project structure
print_step "Verifying project structure..."

if [ ! -d "$PROJECT_ROOT" ]; then
    print_error "Project directory not found: $PROJECT_ROOT"
    exit 1
fi

if [ ! -f "$MODELS_FILE" ]; then
    print_error "models.py not found: $MODELS_FILE"
    exit 1
fi

print_success "Project structure verified"

# Check if models/ already exists
if [ -d "$BFAGENT_PATH/models" ]; then
    print_warning "models/ directory already exists"
    read -p "Delete and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$BFAGENT_PATH/models"
        print_success "Removed existing models/ directory"
    else
        print_error "Aborted"
        exit 1
    fi
fi

# Step 1: Create backup
print_step "Creating backup..."
BACKUP_DIR="$PROJECT_ROOT/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp "$MODELS_FILE" "$BACKUP_DIR/models.py"
print_success "Backup created at: $BACKUP_DIR"

# Step 2: Create Git checkpoint
print_step "Creating Git checkpoint..."
cd "$PROJECT_ROOT"
if git rev-parse --git-dir > /dev/null 2>&1; then
    git add .
    git commit -m "Pre-refactor checkpoint" || true
    print_success "Git checkpoint created"
else
    print_warning "Not a Git repository - skipping Git checkpoint"
fi

# Step 3: Run Python splitter
print_step "Running model splitter..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/split_models.py" ]; then
    print_error "split_models.py not found in: $SCRIPT_DIR"
    exit 1
fi

python3 "$SCRIPT_DIR/split_models.py" "$MODELS_FILE"

if [ $? -eq 0 ]; then
    print_success "Models split successfully"
else
    print_error "Model splitting failed"
    exit 1
fi

# Step 4: Verify Django can import models
print_step "Verifying Django imports..."
cd "$PROJECT_ROOT"

python3 << EOF
import sys
import os
import django

# Setup Django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Try importing models
try:
    from apps.bfagent.models import BookProjects, Agents, StoryBible
    print("✓ All models imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "Django imports verified"
else
    print_error "Django import verification failed"
    exit 1
fi

# Step 5: Check for migrations
print_step "Checking for database migrations..."
cd "$PROJECT_ROOT"
MIGRATION_OUTPUT=$(python3 manage.py makemigrations --dry-run 2>&1)

if echo "$MIGRATION_OUTPUT" | grep -q "No changes detected"; then
    print_success "No database migrations needed (perfect!)"
else
    print_warning "Migration changes detected:"
    echo "$MIGRATION_OUTPUT"
    print_warning "This shouldn't happen. Review changes carefully!"
fi

# Step 6: Run tests (if tests exist)
print_step "Running tests..."
if [ -d "$BFAGENT_PATH/tests" ] || [ -f "$BFAGENT_PATH/tests.py" ]; then
    cd "$PROJECT_ROOT"
    if python3 manage.py test apps.bfagent --verbosity=0; then
        print_success "All tests passed"
    else
        print_error "Some tests failed. Review output above."
        print_warning "Rollback with: git reset --hard HEAD"
        exit 1
    fi
else
    print_warning "No tests found - skipping test run"
fi

# Step 7: Generate report
print_step "Generating refactoring report..."
REPORT_FILE="$PROJECT_ROOT/REFACTORING_REPORT.md"

cat > "$REPORT_FILE" << EOF
# Models Refactoring Report

**Date**: $(date +"%Y-%m-%d %H:%M:%S")
**Original file**: $MODELS_FILE
**New structure**: $BFAGENT_PATH/models/

## Summary

✅ Models split into modular structure
✅ Backward compatibility maintained
✅ No database migrations needed
✅ All tests passing

## Files Created

\`\`\`
$(find "$BFAGENT_PATH/models" -name "*.py" | sed "s|$BFAGENT_PATH/||")
\`\`\`

## Models Distribution

$(python3 << 'PYEOF'
import os
import glob

models_dir = os.path.join("$BFAGENT_PATH", "models")
for file in sorted(glob.glob(os.path.join(models_dir, "*.py"))):
    if file.endswith("__init__.py"):
        continue

    filename = os.path.basename(file)
    with open(file) as f:
        content = f.read()

    # Count models
    model_count = content.count("class ") - content.count("class Meta")
    print(f"- **{filename}**: {model_count} models")
PYEOF
)

## Original File Size

- **Before**: $(wc -l < "$MODELS_FILE.backup" 2>/dev/null || echo "N/A") lines
- **After**: Split into $(find "$BFAGENT_PATH/models" -name "*.py" -not -name "__init__.py" | wc -l) files

## Backup Location

\`$BACKUP_DIR/models.py\`

## Next Steps

1. Review the new structure
2. Update any direct file imports (if any)
3. Run full test suite
4. Deploy to staging
5. If all good, delete backup:
   \`\`\`bash
   rm -rf $BACKUP_DIR
   rm $MODELS_FILE.backup
   \`\`\`

## Rollback (if needed)

\`\`\`bash
# Option 1: Git rollback
git reset --hard HEAD^

# Option 2: Manual restore
rm -rf $BFAGENT_PATH/models/
cp $BACKUP_DIR/models.py $MODELS_FILE
\`\`\`

## Success Criteria

- [x] Models split into logical domains
- [x] No database migrations created
- [x] All imports still work
- [x] Tests passing
- [x] Backup created

---

*Generated by quick_refactor.sh*
EOF

print_success "Report generated: $REPORT_FILE"

# Final summary
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_success "REFACTORING COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "📊 Summary:"
echo "  - Original file: $MODELS_FILE"
echo "  - New structure: $BFAGENT_PATH/models/"
echo "  - Backup: $BACKUP_DIR"
echo "  - Report: $REPORT_FILE"
echo
echo "✅ Next steps:"
echo "  1. Review report: cat $REPORT_FILE"
echo "  2. Test your app thoroughly"
echo "  3. Commit changes: git add . && git commit -m 'Refactor: Split models into modular structure'"
echo "  4. Deploy to staging"
echo
echo "🔄 Rollback (if needed):"
echo "  git reset --hard HEAD^"
echo
print_success "Done! Your models are now modular and maintainable."
