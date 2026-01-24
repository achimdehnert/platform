# Install bfagent_mcp und führe Tests aus
# Run: .\INSTALL_AND_TEST.ps1

Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  bfagent_mcp Installation & Test" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan

# Step 1: Installation
Write-Host "📦 Installiere bfagent_mcp..." -ForegroundColor Yellow
Set-Location packages\bfagent_mcp
pip install -e . --force-reinstall --no-deps
Set-Location ..\..

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Installation fehlgeschlagen!`n" -ForegroundColor Red
    exit 1
}
Write-Host "`n✅ Installation erfolgreich`n" -ForegroundColor Green

# Step 2: TEST 1 - Basic Import
Write-Host "🧪 TEST 1: Import ohne Django" -ForegroundColor Yellow
python test_mcp_simple.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ TEST 1 FEHLGESCHLAGEN`n" -ForegroundColor Red
    exit 1
}
Write-Host "`n✅ TEST 1 BESTANDEN`n" -ForegroundColor Green

# Step 3: TEST 2 - Django Integration  
Write-Host "🧪 TEST 2: Django Integration" -ForegroundColor Yellow
Get-Content test_mcp_with_manage.py | python manage.py shell

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ TEST 2 FEHLGESCHLAGEN`n" -ForegroundColor Red
    exit 1
}
Write-Host "`n✅ TEST 2 BESTANDEN`n" -ForegroundColor Green

# Success!
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  🎉 FERTIG!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ✅ bfagent_mcp installiert" -ForegroundColor Green
Write-Host "  ✅ Lazy Loading funktioniert" -ForegroundColor Green
Write-Host "  ✅ Django Integration OK" -ForegroundColor Green
Write-Host "  ✅ Models verfügbar" -ForegroundColor Green
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "Verwendung:" -ForegroundColor Cyan
Write-Host "  # Ohne Django:" -ForegroundColor Gray
Write-Host "  import bfagent_mcp" -ForegroundColor Gray
Write-Host ""
Write-Host "  # Mit Django:" -ForegroundColor Gray  
Write-Host "  import bfagent_mcp" -ForegroundColor Gray
Write-Host "  Domain = bfagent_mcp.models.Domain" -ForegroundColor Gray
Write-Host ""
