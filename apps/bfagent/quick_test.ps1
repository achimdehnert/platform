# Quick Django Test Script
Write-Host "Testing Django with SQLite..." -ForegroundColor Cyan

# Use venv Python directly
$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
& ".\venv\Scripts\python.exe" manage.py check --deploy

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Django Check PASSED!`n" -ForegroundColor Green
    Write-Host "Starting Django Server..." -ForegroundColor Yellow
    & ".\venv\Scripts\python.exe" manage.py runserver 8000
} else {
    Write-Host "`n❌ Django Check FAILED!`n" -ForegroundColor Red
}
