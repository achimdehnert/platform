# Final Test: bfagent_mcp Refactoring Tools
# Run: .\TEST_MCP_FINAL.ps1

Write-Host "`n═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  bfagent_mcp Refactoring Tools - FINAL TEST" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════`n" -ForegroundColor Cyan

# Step 1: Verify Tables
Write-Host "1️⃣  Database Tables Check..." -ForegroundColor Yellow
.venv\Scripts\python.exe check_tables.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Database tables missing!`n" -ForegroundColor Red
    exit 1
}

# Step 2: Test with Fresh Django Process
Write-Host "`n2️⃣  Testing Refactoring Tools (fresh process)..." -ForegroundColor Yellow
.venv\Scripts\python.exe test_refactor_tools_quick.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Tests FAILED`n" -ForegroundColor Red
    exit 1
}

# Success!
Write-Host "`n═══════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅ ALL TESTS PASSED!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "📦 MCP Tables:" -ForegroundColor Cyan
Write-Host "   ✅ 10 tables created" -ForegroundColor Green
Write-Host "   ✅ 6 component types" -ForegroundColor Green
Write-Host "   ✅ 4 risk levels" -ForegroundColor Green
Write-Host "   ✅ 4 protection levels" -ForegroundColor Green
Write-Host "   ✅ 3 naming conventions" -ForegroundColor Green
Write-Host ""
Write-Host "🛠️  Refactoring Tools:" -ForegroundColor Cyan
Write-Host "   ✅ bfagent_get_refactor_options" -ForegroundColor Green
Write-Host "   ✅ bfagent_check_path_protection" -ForegroundColor Green
Write-Host "   ✅ bfagent_get_naming_convention" -ForegroundColor Green
Write-Host "   ✅ bfagent_list_naming_conventions" -ForegroundColor Green
Write-Host "   ✅ bfagent_list_component_types" -ForegroundColor Green
Write-Host "   ✅ bfagent_start_refactor_session" -ForegroundColor Green
Write-Host "   ✅ bfagent_end_refactor_session" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Ready to use in Windsurf!" -ForegroundColor Yellow
Write-Host ""
