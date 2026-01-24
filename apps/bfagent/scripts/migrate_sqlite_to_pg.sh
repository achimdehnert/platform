#!/bin/bash
# SQLite to PostgreSQL Migration Script
# Works by temporarily switching database configs

set -e

echo "============================================================"
echo "SQLite → PostgreSQL Migration"
echo "============================================================"
echo ""

# Step 1: Export from SQLite
echo "📤 STEP 1: Exporting from SQLite..."
echo ""

# Temporarily override to use SQLite
export DATABASE_ENGINE="sqlite3"
python manage.py dumpdata \
    --exclude contenttypes \
    --exclude auth.permission \
    --exclude sessions.session \
    --exclude admin.logentry \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    --output fixtures/sqlite_backup.json

echo ""
echo "✅ Export complete: fixtures/sqlite_backup.json"
echo ""

# Step 2: Import to PostgreSQL
echo "📥 STEP 2: Importing to PostgreSQL..."
echo ""

# Use PostgreSQL (already configured in development.py)
unset DATABASE_ENGINE
python manage.py loaddata fixtures/sqlite_backup.json

echo ""
echo "✅ Import complete!"
echo ""

# Step 3: Verify
echo "🔍 STEP 3: Verifying migration..."
python -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM auth_user')
user_count = cursor.fetchone()[0]
print(f'  Users in PostgreSQL: {user_count}')
cursor.execute('SELECT COUNT(*) FROM django_content_type')
ct_count = cursor.fetchone()[0]
print(f'  Content Types: {ct_count}')
"

echo ""
echo "============================================================"
echo "✅ Migration Complete!"
echo "============================================================"
