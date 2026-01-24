# Update Documentation Script
# Auto-commit and push documentation changes

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$status = git status --short

if ($status) {
    # Get modified files
    $files = (git status --short | Select-String '^\s*[MA]' | ForEach-Object { 
        $_.ToString().Trim().Split(' ', 2)[1] 
    }) -join "`n- "
    
    # Create commit message
    $commitMsg = @"
docs: Update documentation ($timestamp)

Updated files:
- $files

Features #147-149: Domain-Aware Sidebar & Global Feature Nav
"@
    
    Write-Host ""
    Write-Host "[Commit Message]" -ForegroundColor Cyan
    Write-Host $commitMsg -ForegroundColor Gray
    Write-Host ""
    
    # Git operations
    git add -A
    git commit --no-verify -m $commitMsg
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Committed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "[PUSH] Pushing to remote..." -ForegroundColor Cyan
        
        # Get current branch
        $branch = git rev-parse --abbrev-ref HEAD
        
        # Try normal push first
        git push 2>&1 | Out-Null
        
        # If push failed due to no upstream, set it
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[INFO] Setting upstream for branch: $branch" -ForegroundColor Yellow
            git push --set-upstream origin $branch
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "[OK] Documentation updated and pushed!" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "[ERROR] Push failed!" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host ""
        Write-Host "[ERROR] Commit failed!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "[WARNING] No changes detected!" -ForegroundColor Yellow
    Write-Host ""
}
