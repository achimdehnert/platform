# Quick test if Django is available in current environment
Write-Host "🔍 Checking Django..." -ForegroundColor Cyan
python -c "import django; print(f'✅ Django {django.VERSION}')"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🧪 Running Django test..." -ForegroundColor Yellow
    python test_mcp_django.py
} else {
    Write-Host "`n⚠️  Django not found in current Python environment!" -ForegroundColor Red
    Write-Host "Please make sure .venv is activated:" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
}
