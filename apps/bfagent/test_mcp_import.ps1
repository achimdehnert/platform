# Test bfagent_mcp Installation und Lazy Loading

Write-Host "`n🧪 TEST 1: Import ohne Django" -ForegroundColor Cyan
python -c @"
import bfagent_mcp
print('✅ Import SUCCESS')
print(f'✅ Version: {bfagent_mcp.__version__}')
print(f'✅ Server: {bfagent_mcp._HAS_SERVER}')
print(f'✅ models object: {hasattr(bfagent_mcp, \"models\")}')
"@

Write-Host "`n🧪 TEST 2: Models mit Django" -ForegroundColor Cyan
python test_mcp_models.py

Write-Host "`n✅ ALLE TESTS BESTANDEN!" -ForegroundColor Green
