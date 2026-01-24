# SQLite to PostgreSQL Migration Script for Windows
# Automatically exports from SQLite and imports to PostgreSQL

$ErrorActionPreference = "Stop"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "SQLite → PostgreSQL Migration" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# Change to project directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Split-Path -Parent $scriptPath
Set-Location $projectPath

# Create fixtures directory
$fixturesDir = Join-Path $projectPath "fixtures"
if (-not (Test-Path $fixturesDir)) {
    New-Item -ItemType Directory -Path $fixturesDir | Out-Null
}

$backupFile = Join-Path $fixturesDir "sqlite_backup.json"

# Step 1: Export from SQLite
Write-Host "📤 STEP 1: Exporting from SQLite..." -ForegroundColor Yellow
Write-Host ""

# Temporarily point Django to SQLite
$env:USE_SQLITE = "1"

try {
    # Export all data except system tables
    python manage.py dumpdata `
        --exclude contenttypes `
        --exclude sessions.session `
        --exclude admin.logentry `
        --natural-foreign `
        --natural-primary `
        --indent 2 `
        --output $backupFile

    Write-Host ""
    Write-Host "✅ Export complete: $backupFile" -ForegroundColor Green

    # Show file size
    $fileSize = (Get-Item $backupFile).Length / 1KB
    Write-Host "   File size: $([math]::Round($fileSize, 2)) KB" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host "❌ Export failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Switch to PostgreSQL and import
Write-Host "📥 STEP 2: Importing to PostgreSQL..." -ForegroundColor Yellow
Write-Host ""

# Remove SQLite override to use PostgreSQL
Remove-Item Env:USE_SQLITE -ErrorAction SilentlyContinue

try {
    # Load data into PostgreSQL
    python manage.py loaddata $backupFile

    Write-Host ""
    Write-Host "✅ Import complete!" -ForegroundColor Green
    Write-Host ""

} catch {
    Write-Host "❌ Import failed: $_" -ForegroundColor Red
    Write-Host "   You can retry with: python manage.py loaddata $backupFile" -ForegroundColor Yellow
    exit 1
}

# Step 3: Verify migration
Write-Host "🔍 STEP 3: Verifying migration..." -ForegroundColor Yellow
Write-Host ""

$verifyScript = @"
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

cursor = connection.cursor()

# Check users
user_count = User.objects.count()
print(f'  ✅ Users: {user_count}')

# Check content types
ct_count = ContentType.objects.count()
print(f'  ✅ Content Types: {ct_count}')

# Check database info
cursor.execute('SELECT version()')
version = cursor.fetchone()[0]
print(f'  ✅ PostgreSQL: {version.split(\",\")[0]}')

# Check total rows
cursor.execute(\"\"\"
    SELECT SUM(n_live_tup)
    FROM pg_stat_user_tables
\"\"\")
total_rows = cursor.fetchone()[0] or 0
print(f'  ✅ Total rows: {total_rows:,}')
"@

python -c $verifyScript

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ Migration Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test your application: python manage.py runserver" -ForegroundColor White
Write-Host "  2. Backup SQLite file: bfagent.db (keep as backup)" -ForegroundColor White
Write-Host "  3. Use PostgreSQL from now on!" -ForegroundColor White
Write-Host ""
