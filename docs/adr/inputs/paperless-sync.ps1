# paperless-sync.ps1
# Watches C:\ScanSnap\Paperless for new files and moves them to
# the Paperless consume folder (mapped as Z:\) via WireGuard+SMB.
#
# Usage: Run in PowerShell, or set up as Scheduled Task at logon.
#   powershell -ExecutionPolicy Bypass -File C:\ScanSnap\paperless-sync.ps1

$watchFolder = "C:\ScanSnap\Paperless"
$destDrive   = "Z:\"
$logFile     = "C:\ScanSnap\sync.log"

# Ensure folders exist
New-Item -ItemType Directory -Force -Path $watchFolder | Out-Null

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Tee-Object -FilePath $logFile -Append
}

Write-Log "Paperless Sync started. Watching: $watchFolder -> $destDrive"

# FileSystemWatcher for instant detection
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchFolder
$watcher.Filter = "*.*"
$watcher.IncludeSubdirectories = $false
$watcher.EnableRaisingEvents = $true

$action = {
    Start-Sleep -Seconds 2  # Wait for file to finish writing
    $path = $Event.SourceEventArgs.FullPath
    $name = $Event.SourceEventArgs.Name

    if (Test-Path $path) {
        try {
            # Ensure Z: is connected
            if (-not (Test-Path "Z:\")) {
                net use Z: \\10.99.0.1\paperless-consume /user:scansnap ScanSnap2026! /persistent:yes 2>$null
                Start-Sleep -Seconds 1
            }

            Move-Item -Path $path -Destination "Z:\$name" -Force
            $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            "$ts  SYNCED: $name -> Paperless" | Tee-Object -FilePath "C:\ScanSnap\sync.log" -Append
        }
        catch {
            $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            "$ts  ERROR: $name - $_" | Tee-Object -FilePath "C:\ScanSnap\sync.log" -Append
        }
    }
}

Register-ObjectEvent $watcher "Created" -Action $action | Out-Null

Write-Log "Watcher active. Press Ctrl+C to stop."

# Keep script running
while ($true) {
    # Also check for any leftover files every 30 seconds
    $files = Get-ChildItem -Path $watchFolder -File -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        try {
            if (-not (Test-Path "Z:\")) {
                net use Z: \\10.99.0.1\paperless-consume /user:scansnap ScanSnap2026! /persistent:yes 2>$null
                Start-Sleep -Seconds 1
            }
            Move-Item -Path $f.FullName -Destination "Z:\$($f.Name)" -Force
            Write-Log "SYNCED (poll): $($f.Name) -> Paperless"
        }
        catch {
            # File might still be written, skip
        }
    }
    Start-Sleep -Seconds 30
}
