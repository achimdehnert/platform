# Test bfagent_mcp Installation
# Dieses Script im Terminal ausführen: .\RUN_TESTS.ps1

Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  bfagent_mcp Installation Tests" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan

# Check if venv is active
$pythonPath = (Get-Command python).Source
if ($pythonPath -like "*\.venv\*") {
    Write-Host "✅ Virtual environment aktiv: $pythonPath`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  System Python aktiv: $pythonPath" -ForegroundColor Yellow
    Write-Host "HINWEIS: Aktiviere .venv für vollständige Tests`n" -ForegroundColor Yellow
}

Write-Host "🧪 TEST 1: Import ohne Django" -ForegroundColor Yellow
python test_mcp_simple.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ TEST 1 BESTANDEN`n" -ForegroundColor Green
} else {
    Write-Host "`n❌ TEST 1 FEHLGESCHLAGEN`n" -ForegroundColor Red
    exit 1
}

Write-Host "🧪 TEST 2: Models mit Django (via manage.py)" -ForegroundColor Yellow
# Use manage.py shell to ensure Django is properly configured
Get-Content test_mcp_with_manage.py | python manage.py shell

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ TEST 2 BESTANDEN`n" -ForegroundColor Green
} else {
    Write-Host "`n❌ TEST 2 FEHLGESCHLAGEN`n" -ForegroundColor Red
    exit 1
}

Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🎉 ALLE TESTS BESTANDEN!" -ForegroundColor Green
Write-Host "  ✅ bfagent_mcp ist installiert" -ForegroundColor Green
Write-Host "  ✅ Lazy Loading funktioniert" -ForegroundColor Green
Write-Host "  ✅ Django Integration OK" -ForegroundColor Green
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan
