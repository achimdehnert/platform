# BFAgent DB Reset mit System-Daten
# ===================================
# Resettet bfagent.db und behält ALLE System-Daten
#
# Django verwendet: bfagent.db (config/settings/base.py)
# NICHT: db.sqlite3

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host " BFAgent DB Reset" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. Python-Prozesse stoppen
Write-Host "1. Stoppe Python-Prozesse..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Write-Host "   ✅ Prozesse gestoppt" -ForegroundColor Green

# 2. Backup erstellen
Write-Host "2. Erstelle Backup..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "bfagent_backup_$timestamp.db"

if (Test-Path "bfagent.db") {
    Copy-Item "bfagent.db" $backupFile
    $size = (Get-Item $backupFile).Length / 1MB
    Write-Host "   ✅ Backup: $backupFile ($([math]::Round($size, 1)) MB)" -ForegroundColor Green
} else {
    Write-Host "   ❌ bfagent.db nicht gefunden!" -ForegroundColor Red
    exit 1
}

# 3. Alte DB löschen
Write-Host "3. Lösche alte DB..." -ForegroundColor Yellow
Remove-Item bfagent.db -Force -ErrorAction Stop
if (Test-Path "bfagent.db-shm") { Remove-Item "bfagent.db-shm" -Force }
if (Test-Path "bfagent.db-wal") { Remove-Item "bfagent.db-wal" -Force }
Write-Host "   ✅ DB gelöscht" -ForegroundColor Green

# 4. Migrations
Write-Host "4. Führe Migrations aus..." -ForegroundColor Yellow
python manage.py migrate 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Migration fehlgeschlagen!" -ForegroundColor Red
    Write-Host "   Backup verfügbar: $backupFile" -ForegroundColor Yellow
    exit 1
}
Write-Host "   ✅ Fresh DB erstellt" -ForegroundColor Green

# 5. System-Daten restore
Write-Host "5. Restore System-Daten..." -ForegroundColor Yellow

$pythonScript = @"
import sqlite3
import sys

try:
    # Connect to both databases
    dst = sqlite3.connect('bfagent.db')
    dst.execute(f'ATTACH DATABASE ''$backupFile'' AS backup')

    # System tables to restore
    tables = [
        'core_domain', 'core_handler', 'core_handlercategory',
        'llms', 'agents', 'agent_types',
        'domain_arts', 'domain_types', 'domain_phases',
        'handlers', 'action_handlers',
        'control_center_workflowdomain',
        'control_center_navigationsection',
        'control_center_navigationitem',
        'writing_hub_handlerphase',
        'genagent_phase', 'genagent_action', 'genagent_customdomain',
        'bfagent_mcp_domain', 'bfagent_mcp_phase', 'bfagent_mcp_handler',
        'bfagent_mcp_bestpractice', 'bfagent_mcp_prompttemplate'
    ]

    restored = 0
    skipped = 0

    for table in tables:
        try:
            # Check if table exists in backup
            cursor = dst.execute(f'SELECT COUNT(*) FROM backup.sqlite_master WHERE type=\"table\" AND name=\"{table}\"')
            if cursor.fetchone()[0] == 0:
                skipped += 1
                continue

            # Copy data
            dst.execute(f'INSERT OR IGNORE INTO {table} SELECT * FROM backup.{table}')
            count = dst.execute(f'SELECT changes()').fetchone()[0]
            if count > 0:
                print(f'  ✓ {table}: {count} rows')
                restored += 1
        except Exception as e:
            print(f'  ⚠ {table}: {str(e)[:50]}')
            skipped += 1

    dst.commit()
    dst.close()

    print(f'\n✅ Restored {restored} tables, skipped {skipped}')
    sys.exit(0)

except Exception as e:
    print(f'\n❌ Error: {e}')
    sys.exit(1)
"@

$pythonScript | python
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ⚠️  Einige Daten konnten nicht kopiert werden" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ System-Daten wiederhergestellt" -ForegroundColor Green
}

# 6. Abschluss
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host " ✅ Reset abgeschlossen!" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backup gespeichert: $backupFile" -ForegroundColor Green
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Yellow
Write-Host "  1. python manage.py createsuperuser" -ForegroundColor White
Write-Host "  2. python manage.py runserver" -ForegroundColor White
Write-Host "  3. http://localhost:8000/cad-hub/" -ForegroundColor White
Write-Host ""
