# Restart Django Server with Cache Clearing
Write-Host "🧹 Clearing Python Cache..." -ForegroundColor Cyan

# Clear all __pycache__ directories
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Write-Host "✅ Cache cleared!" -ForegroundColor Green

Write-Host "`n🚀 Starting Django Server..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe manage.py runserver
