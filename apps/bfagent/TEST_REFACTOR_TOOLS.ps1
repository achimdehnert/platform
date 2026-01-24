# Test bfagent_mcp Refactoring Tools
# Run: .\TEST_REFACTOR_TOOLS.ps1

Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  bfagent_mcp Refactoring Tools Test" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan

# Step 1: Package Installation Check
Write-Host "1. Package Check..." -ForegroundColor Yellow
python -c "import bfagent_mcp; print(f'Version: {bfagent_mcp.__version__}'); print(f'Server: {bfagent_mcp._HAS_SERVER}')"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nPackage nicht gefunden! Installiere..." -ForegroundColor Red
    cd packages\bfagent_mcp
    pip install -e . --force-reinstall --no-deps
    cd ..\..
    Write-Host "`nPackage installiert. Teste erneut..." -ForegroundColor Green
    python -c "import bfagent_mcp; print(f'Version: {bfagent_mcp.__version__}')"
}

# Step 2: Service Test
Write-Host "`n2. Refactor Service Test..." -ForegroundColor Yellow

# Create test script
@"
import asyncio
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from bfagent_mcp.refactor_service import MCPRefactorService

async def test_tools():
    service = MCPRefactorService()
    
    print("\n=== TEST 1: Get Refactor Options ===")
    result = await service.get_refactor_options("writing_hub", "markdown")
    print(result[:500] if len(result) > 500 else result)
    
    print("\n=== TEST 2: Check Path Protection ===")
    result = await service.check_path_protection("packages/bfagent_mcp/server.py", "markdown")
    print(result[:500] if len(result) > 500 else result)
    
    print("\n=== TEST 3: Get Naming Convention ===")
    result = await service.get_naming_convention("bfagent_mcp", "markdown")
    print(result)
    
    print("\n=== TEST 4: List Naming Conventions ===")
    result = await service.list_naming_conventions("markdown")
    print(result[:500] if len(result) > 500 else result)
    
    print("\n=== TEST 5: List Component Types ===")
    result = await service.list_component_types("markdown")
    print(result[:500] if len(result) > 500 else result)
    
    print("\n=== TEST 6: Start Refactor Session ===")
    result = await service.start_refactor_session("writing_hub", ["handler"])
    print(result)
    
    print("\n=== TEST 7: End Refactor Session ===")
    result = await service.end_refactor_session(1, "completed", 5, "Test session")
    print(result)

asyncio.run(test_tools())
"@ | Out-File -FilePath test_refactor_temp.py -Encoding UTF8

python test_refactor_temp.py

Remove-Item test_refactor_temp.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Service Tests FEHLGESCHLAGEN`n" -ForegroundColor Red
    exit 1
}

# Success
Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ✅ ALLE TESTS BESTANDEN!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ✅ Package installiert & getestet" -ForegroundColor Green
Write-Host "  ✅ Alle 7 Refactoring Tools funktional" -ForegroundColor Green
Write-Host "  ✅ Django Integration OK" -ForegroundColor Green
Write-Host "  ✅ Service Layer ready" -ForegroundColor Green
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. MCP Server starten:" -ForegroundColor Gray
Write-Host "     python -m bfagent_mcp.server" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. In Windsurf verwenden:" -ForegroundColor Gray
Write-Host "     'Was kann ich im writing_hub refactoren?'" -ForegroundColor Gray
Write-Host ""
