# Memory Bank Performance Monitor
# Based on Windsurf Memory Bank Best Practices

Write-Host "📊 Windsurf Memory Bank Performance Monitor" -ForegroundColor Cyan
Write-Host "=" * 50

# Performance Thresholds (from best practices)
$OPTIMAL_TOTAL = 30000      # 30 KB
$WARNING_THRESHOLD = 50000  # 50 KB
$CRITICAL_THRESHOLD = 100000 # 100 KB
$MAX_FILE_SIZE = 15000      # 15 KB per file

# Analyze current memory bank
$memoryBankPath = "."
$totalSize = 0
$fileCount = 0
$oversizedFiles = @()
$healthScore = 100

Write-Host "🔍 Analyzing Memory Bank Files..." -ForegroundColor Yellow

Get-ChildItem -Path $memoryBankPath -Filter "*.md" | ForEach-Object {
    $size = $_.Length
    $totalSize += $size
    $fileCount++

    $sizeKB = [math]::Round($size / 1024, 1)

    if ($size -gt $MAX_FILE_SIZE) {
        $oversizedFiles += @{
            Name = $_.Name
            Size = $sizeKB
            Overage = [math]::Round(($size - $MAX_FILE_SIZE) / 1024, 1)
        }
        $healthScore -= 15
        Write-Host "   ⚠️  $($_.Name): ${sizeKB}KB (>${MAX_FILE_SIZE/1024}KB limit)" -ForegroundColor Red
    } else {
        Write-Host "   ✅ $($_.Name): ${sizeKB}KB" -ForegroundColor Green
    }
}

# Calculate metrics
$totalKB = [math]::Round($totalSize / 1024, 1)
$avgFileSize = [math]::Round($totalSize / $fileCount / 1024, 1)

# Determine status
$status = "OPTIMAL"
$statusColor = "Green"
if ($totalSize -gt $CRITICAL_THRESHOLD) {
    $status = "CRITICAL"
    $statusColor = "Red"
    $healthScore = 0
} elseif ($totalSize -gt $WARNING_THRESHOLD) {
    $status = "WARNING"
    $statusColor = "Yellow"
    $healthScore = [math]::Max(30, $healthScore - 20)
}

Write-Host ""
Write-Host "📈 MEMORY BANK PERFORMANCE REPORT" -ForegroundColor Cyan
Write-Host "=" * 40
Write-Host "Total Size:     ${totalKB}KB" -ForegroundColor White
Write-Host "File Count:     $fileCount files" -ForegroundColor White
Write-Host "Avg File Size:  ${avgFileSize}KB" -ForegroundColor White
Write-Host "Status:         $status" -ForegroundColor $statusColor
Write-Host "Health Score:   ${healthScore}%" -ForegroundColor $(if($healthScore -gt 70){"Green"}elseif($healthScore -gt 40){"Yellow"}else{"Red"})

# Recommendations
Write-Host ""
Write-Host "🎯 RECOMMENDATIONS:" -ForegroundColor Cyan

if ($totalSize -gt $CRITICAL_THRESHOLD) {
    Write-Host "   🚨 CRITICAL: Immediate action required!" -ForegroundColor Red
    Write-Host "   • Archive or compress large files immediately" -ForegroundColor Red
    Write-Host "   • Target reduction: $([math]::Round(($totalSize - $OPTIMAL_TOTAL) / 1024, 1))KB" -ForegroundColor Red
} elseif ($totalSize -gt $WARNING_THRESHOLD) {
    Write-Host "   ⚠️  WARNING: Performance degradation likely" -ForegroundColor Yellow
    Write-Host "   • Consider archiving older content" -ForegroundColor Yellow
    Write-Host "   • Compress verbose documentation" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ OPTIMAL: Memory bank is well optimized" -ForegroundColor Green
    Write-Host "   • Continue monitoring file growth" -ForegroundColor Green
}

if ($oversizedFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "📋 OVERSIZED FILES REQUIRING ATTENTION:" -ForegroundColor Yellow
    $oversizedFiles | ForEach-Object {
        Write-Host "   • $($_.Name): $($_.Size)KB (reduce by $($_.Overage)KB)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "💡 OPTIMIZATION TIPS:" -ForegroundColor Cyan
Write-Host "   • Use bullet points instead of paragraphs" -ForegroundColor White
Write-Host "   • Archive old decisions to archive/ folder" -ForegroundColor White
Write-Host "   • Compress code examples and remove redundancy" -ForegroundColor White
Write-Host "   • Use semantic chunking for large topics" -ForegroundColor White

Write-Host ""
Write-Host "🔄 Run this script regularly to maintain optimal performance!" -ForegroundColor Green
