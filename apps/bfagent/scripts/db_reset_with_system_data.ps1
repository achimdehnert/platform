# Database Reset mit System-Daten Erhaltung
# ==========================================
# Automatischer DB-Reset der ALLE System-Daten erhält
#
# Was wird gesichert:
#   - Handlers, LLMs, Agents
#   - Domains, DomainTypes, Phases
#   - Navigation (Sections & Items)
#   - GenAgent Konfiguration
#   - BFAgent MCP Daten
#
# Was wird NICHT gesichert:
#   - User-generierte Inhalte (Projekte, Kapitel, etc.)
#   - Logs, Executions
#   - Temporäre Daten

$ErrorActionPreference = "Stop"

Write-Host "================================" -ForegroundColor Cyan
Write-Host " DB Reset mit System-Daten" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. Alle Python-Prozesse stoppen
Write-Host "1. Stoppe Python-Prozesse..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 2. Backup erstellen
Write-Host "2. Erstelle DB-Backup..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "db_backup_$timestamp.sqlite3"

if (Test-Path "db.sqlite3") {
    Copy-Item "db.sqlite3" $backupFile
    Write-Host "   ✅ Backup erstellt: $backupFile" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Keine DB vorhanden zum Backup" -ForegroundColor Yellow
}

# 3. Alte DB löschen
Write-Host "3. Lösche alte DB..." -ForegroundColor Yellow
Remove-Item db.sqlite3* -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ DB gelöscht" -ForegroundColor Green

# 4. Fresh migrations
Write-Host "4. Führe Migrations aus..." -ForegroundColor Yellow
python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Migration fehlgeschlagen!" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Migrations komplett" -ForegroundColor Green

# 5. System-Daten wiederherstellen (wenn Backup existiert)
if (Test-Path $backupFile) {
    Write-Host "5. Stelle System-Daten wieder her..." -ForegroundColor Yellow

    # SQLite Befehle vorbereiten
    $sqlCommands = @"
ATTACH DATABASE '$backupFile' AS backup;

-- Core Models
INSERT OR IGNORE INTO core_domain SELECT * FROM backup.core_domain;
INSERT OR IGNORE INTO core_handler SELECT * FROM backup.core_handler;
INSERT OR IGNORE INTO core_handlercategory SELECT * FROM backup.core_handlercategory;

-- BFAgent Essential
INSERT OR IGNORE INTO bfagent_llms SELECT * FROM backup.bfagent_llms;
INSERT OR IGNORE INTO bfagent_agents SELECT * FROM backup.bfagent_agents;
INSERT OR IGNORE INTO bfagent_agenttype SELECT * FROM backup.bfagent_agenttype;
INSERT OR IGNORE INTO bfagent_domainart SELECT * FROM backup.bfagent_domainart;
INSERT OR IGNORE INTO bfagent_domaintype SELECT * FROM backup.bfagent_domaintype;
INSERT OR IGNORE INTO bfagent_domainphase SELECT * FROM backup.bfagent_domainphase;
INSERT OR IGNORE INTO bfagent_actionhandler SELECT * FROM backup.bfagent_actionhandler;

-- Control Center
INSERT OR IGNORE INTO control_center_workflowdomain SELECT * FROM backup.control_center_workflowdomain;
INSERT OR IGNORE INTO control_center_navigationsection SELECT * FROM backup.control_center_navigationsection;
INSERT OR IGNORE INTO control_center_navigationitem SELECT * FROM backup.control_center_navigationitem;

-- Writing Hub
INSERT OR IGNORE INTO writing_hub_handlerphase SELECT * FROM backup.writing_hub_handlerphase;

-- GenAgent
INSERT OR IGNORE INTO genagent_phase SELECT * FROM backup.genagent_phase;
INSERT OR IGNORE INTO genagent_action SELECT * FROM backup.genagent_action;
INSERT OR IGNORE INTO genagent_customdomain SELECT * FROM backup.genagent_customdomain;

-- BFAgent MCP
INSERT OR IGNORE INTO bfagent_mcp_domain SELECT * FROM backup.bfagent_mcp_domain;
INSERT OR IGNORE INTO bfagent_mcp_phase SELECT * FROM backup.bfagent_mcp_phase;
INSERT OR IGNORE INTO bfagent_mcp_handler SELECT * FROM backup.bfagent_mcp_handler;
INSERT OR IGNORE INTO bfagent_mcp_bestpractice SELECT * FROM backup.bfagent_mcp_bestpractice;
INSERT OR IGNORE INTO bfagent_mcp_prompttemplate SELECT * FROM backup.bfagent_mcp_prompttemplate;

DETACH DATABASE backup;
"@

    # SQL ausführen
    $sqlCommands | sqlite3 db.sqlite3

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ System-Daten wiederhergestellt" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Warnung: Einige Daten konnten nicht kopiert werden" -ForegroundColor Yellow
    }
} else {
    Write-Host "5. Kein Backup gefunden - übersprungen" -ForegroundColor Yellow
}

# 6. Statistiken
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host " Abgeschlossen!" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Yellow
Write-Host "  1. Superuser erstellen: python manage.py createsuperuser" -ForegroundColor White
Write-Host "  2. Server starten: python manage.py runserver" -ForegroundColor White
Write-Host "  3. CAD Hub testen: http://localhost:8000/cad-hub/" -ForegroundColor White
Write-Host ""
Write-Host "Backup gespeichert in: $backupFile" -ForegroundColor Green
Write-Host ""
