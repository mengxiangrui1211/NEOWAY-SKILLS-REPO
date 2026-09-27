param(
    [Parameter(Mandatory=$true)]
    [string]$LogPath
)

$Host.UI.RawUI.WindowTitle = "N25 Build Log - $env:USERNAME"
$hasError = $false
$timeout = 30
$elapsed = 0

# Wait for log file to appear (with timeout)
while (!(Test-Path $LogPath)) {
    Start-Sleep 1
    $elapsed++
    if ($elapsed -ge $timeout) {
        Write-Host "ERROR: Log file not found after $timeout seconds: $LogPath" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
}

# Tail log and detect build result
Get-Content $LogPath -Wait -Tail 50 | ForEach-Object {
    $_
    # Detect failure markers (Error must be checked before Success)
    if ($_ -match 'make.*Error|build Fail') {
        $hasError = $true
    }
    # Detect end of build
    if ($_ -match 'build Success') {
        # Wait 3 more seconds to catch any trailing Error lines
        Start-Sleep 3
        # Check if any new Error appeared during the delay
        $recentLines = Get-Content $LogPath -Tail 10
        foreach ($line in $recentLines) {
            if ($line -match 'make.*Error|build Fail') {
                $hasError = $true
            }
        }
        if ($hasError) {
            Write-Host ''
            Write-Host '>>> BUILD FAILED! Window stays open, please review errors above. <<<' -ForegroundColor Red
            # Keep window open
            return
        } else {
            Write-Host ''
            Write-Host '>>> BUILD SUCCESS! Window will close in 5 seconds... <<<' -ForegroundColor Green
            Start-Sleep 5
            exit
        }
    }
}
