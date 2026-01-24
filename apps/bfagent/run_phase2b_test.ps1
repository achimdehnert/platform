# Phase 2b Test Runner mit Output-Logging
$ErrorActionPreference = "Continue"
$OutputFile = "phase2b_test_output.txt"

Write-Host "==> Running Phase 2b Tests..." -ForegroundColor Cyan

# Test 1: Check migrations
Write-Host "`n1. Checking migrations..." -ForegroundColor Yellow
python manage.py showmigrations core | Out-File -FilePath $OutputFile -Encoding UTF8

# Test 2: Apply migrations
Write-Host "2. Applying migrations..." -ForegroundColor Yellow
python manage.py migrate core --verbosity 2 | Out-File -FilePath $OutputFile -Append -Encoding UTF8

# Test 3: Quick test
Write-Host "3. Running quick test..." -ForegroundColor Yellow
python quick_test_phase2b.py | Out-File -FilePath $OutputFile -Append -Encoding UTF8

# Test 4: Full test suite
Write-Host "4. Running full test suite..." -ForegroundColor Yellow
python test_phase_2b_migration.py | Out-File -FilePath $OutputFile -Append -Encoding UTF8

Write-Host "`n==> Tests complete! Check $OutputFile for results" -ForegroundColor Green
Write-Host "View output: Get-Content $OutputFile`n" -ForegroundColor Cyan

# Show output
Get-Content $OutputFile
