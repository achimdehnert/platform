# Simple SQLite to PostgreSQL Migration
# Uses Django's dumpdata/loaddata commands

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "SQLite → PostgreSQL Data Migration" -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

# Create fixtures directory
$fixturesDir = Join-Path $projectRoot "fixtures"
if (-not (Test-Path $fixturesDir)) {
    New-Item -ItemType Directory -Path $fixturesDir | Out-Null
}

# Step 1: Export from SQLite using base.py settings
Write-Host "📤 STEP 1: Exporting from SQLite (using config/settings/base.py)..." -ForegroundColor Yellow
Write-Host ""

$env:DJANGO_SETTINGS_MODULE = "config.settings.base"

python manage.py dumpdata `
    --exclude contenttypes `
    --exclude auth.permission `
    --exclude sessions.session `
    --exclude admin.logentry `
    --natural-foreign `
    --natural-primary `
    --indent 2 `
    --output "fixtures/data_backup.json"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Export failed!" -ForegroundColor Red
    exit 1
}

$fileSize = (Get-Item "fixtures/data_backup.json").Length / 1KB
Write-Host "`n✅ Export complete: fixtures/data_backup.json ($([math]::Round($fileSize, 2)) KB)" -ForegroundColor Green

# Step 2: Import to PostgreSQL using development.py settings
Write-Host "`n📥 STEP 2: Importing to PostgreSQL (using config/settings/development.py)..." -ForegroundColor Yellow
Write-Host ""

$env:DJANGO_SETTINGS_MODULE = "config.settings.development"

python manage.py loaddata "fixtures/data_backup.json"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Import failed!" -ForegroundColor Red
    Write-Host "You can retry with: python manage.py loaddata fixtures/data_backup.json" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n✅ Import complete!" -ForegroundColor Green

# Step 3: Verify
Write-Host "`n🔍 STEP 3: Verifying migration..." -ForegroundColor Yellow

python -c "from django.db import connection; from django.contrib.auth.models import User; print(f'  Users: {User.objects.count()}')"

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "✅ Migration Complete!" -ForegroundColor Green
Write-Host "===========================================================`n" -ForegroundColor Cyan
