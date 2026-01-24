# Test bfagent_mcp Installation
# Run: .\TEST_MCP.ps1

Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  bfagent_mcp Installation Tests" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan

# Check Python environment
$pythonPath = (Get-Command python).Source
Write-Host "Python: $pythonPath" -ForegroundColor DarkGray
if ($pythonPath -like "*\.venv\*") {
    Write-Host "✅ Virtual environment aktiv`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  System Python - für Test 2 .venv aktivieren!`n" -ForegroundColor Yellow
}

# TEST 1: Basic Import
Write-Host "🧪 TEST 1: Import ohne Django" -ForegroundColor Yellow
python test_mcp_simple.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ TEST 1 FEHLGESCHLAGEN`n" -ForegroundColor Red
    exit 1
}
Write-Host "`n✅ TEST 1 BESTANDEN`n" -ForegroundColor Green

# TEST 2: Django Integration
Write-Host "🧪 TEST 2: Models mit Django" -ForegroundColor Yellow
Get-Content test_mcp_with_manage.py | python manage.py shell

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ TEST 2 FEHLGESCHLAGEN`n" -ForegroundColor Red
    exit 1
}
Write-Host "`n✅ TEST 2 BESTANDEN`n" -ForegroundColor Green

# Success
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🎉 ALLE TESTS BESTANDEN!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ✅ bfagent_mcp installiert" -ForegroundColor Green
Write-Host "  ✅ Lazy Loading funktioniert" -ForegroundColor Green
Write-Host "  ✅ Django Integration OK" -ForegroundColor Green
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan
