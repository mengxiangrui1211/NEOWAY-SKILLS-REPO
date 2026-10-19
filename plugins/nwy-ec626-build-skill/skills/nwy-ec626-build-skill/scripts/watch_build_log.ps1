param(
    [Parameter(Mandatory=$true)]
    [string]$LogPath,
    [int]$ProcId = 0   # build_nwy.bat cmd PID; >0 -> kill its process tree when build ends
)

$Host.UI.RawUI.WindowTitle = "EC626 Build Log - $env:USERNAME"
$hasError = $false
$menuLoops = 0
$done = $false
$deadline = (Get-Date).AddMinutes(60)

# build_nwy.bat is a LOOPING menu: after every finished action it re-shows the
# menu, and "set /p" keeps the previous selection at EOF -> infinite rebuild
# loop (tested 2026-10-12: 40+ rounds). Killing the tree when the build ends
# is the hard stop. Same failure marker set as in SKILL.md.
$failRe = 'make.*Error|make.*\*\*\*|^fail\s*$|GCCLIB_PATH setting'

function Kill-BuildTree {
    if ($ProcId -gt 0) { taskkill /PID $ProcId /T /F 2>$null | Out-Null }
}

# Wait for log file to appear (with timeout)
while (!(Test-Path $LogPath)) {
    Start-Sleep 1
    $elapsed++
    if ($elapsed -ge 30) {
        Write-Host "ERROR: Log file not found after 30 seconds: $LogPath" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
}

# Tail log and detect build result
Get-Content $LogPath -Wait -Tail 50 | ForEach-Object {
    if ($done) { return }
    $_
    # Detect failure markers (Error must be checked before Success)
    if ($_ -match $failRe) {
        $hasError = $true
    }
    # the bat re-shows its menu after EVERY finished action;
    # prompt seen twice = one build has completed
    if ($_ -match 'Please select project') { $menuLoops++ }

    if ($_ -match 'build successfully|clean.*done ok') {
        # Kill FIRST: the 3s grace before kill let the menu loop start a second
        # build round (SKILL.md pitfall 7). Buffered trailing lines still land
        # in the log afterwards, so the error recheck stays valid.
        Kill-BuildTree
        Start-Sleep 2
        foreach ($line in (Get-Content $LogPath -Tail 15)) {
            if ($line -match $failRe) { $hasError = $true }
        }
        $done = $true
        if ($hasError) {
            Write-Host ''
            Write-Host '>>> BUILD FAILED! Process tree killed. Window stays open, review errors above. <<<' -ForegroundColor Red
        } else {
            Write-Host ''
            Write-Host '>>> BUILD SUCCESS! Process tree killed (prevents menu-loop rebuild). Closing in 5 seconds... <<<' -ForegroundColor Green
            Start-Sleep 5
            exit
        }
    }
    elseif ($menuLoops -ge 2) {
        # success line was missed (e.g. watcher attached late) but the menu
        # looping back proves a build finished -> stop and judge by log tail
        Kill-BuildTree
        Start-Sleep 2
        foreach ($line in (Get-Content $LogPath -Tail 15)) {
            if ($line -match $failRe) { $hasError = $true }
        }
        $done = $true
        if ($hasError) {
            Write-Host ''
            Write-Host '>>> BUILD FINISHED (with errors). Process tree killed. Review errors above. <<<' -ForegroundColor Red
        } else {
            Write-Host ''
            Write-Host '>>> BUILD FINISHED! Process tree killed. Closing in 5 seconds... <<<' -ForegroundColor Green
            Start-Sleep 5
            exit
        }
    }
    elseif ((Get-Date) -gt $deadline) {
        Kill-BuildTree
        $done = $true
        Write-Host ''
        Write-Host '>>> TIMEOUT after 60 min - process tree killed. Review log above. <<<' -ForegroundColor Yellow
    }
}
