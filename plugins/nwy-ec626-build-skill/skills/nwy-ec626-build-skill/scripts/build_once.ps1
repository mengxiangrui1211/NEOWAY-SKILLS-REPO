# build_once.ps1 - one-shot EC626 build wrapper for nwy-ec626-build-skill.
# ASCII only (see SKILL.md pitfall 5). Starts build_nwy.bat once, waits for it to
# end (watchdog kills the runaway menu loop), prints "RESULT: SUCCESS|FAIL ..." and
# exits 0/1 so a background task notification carries the verdict to the agent.
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('firmware','bootloader','clean','unilog')]
    [string]$Mode,
    [string]$Project = '',
    [string]$PLAT = '',
    [string]$SkillDir = ''
)

$ErrorActionPreference = 'Stop'

# No hardcoded defaults: this skill is shared across machines and EC626 branches
# (SKILL.md pitfall 9). Project names, PLAT path and skill path all vary.

# Skill dir is wherever this script actually lives.
if (-not $SkillDir) { $SkillDir = Split-Path $PSScriptRoot -Parent }

# PLAT = the directory holding build_nwy.bat. Never guess it (pitfall 8).
if (-not $PLAT) {
    $roots = @()
    foreach ($r in @((Get-Location).Path, (Split-Path (Split-Path (Split-Path $SkillDir -Parent) -Parent) -Parent))) {
        if ($r -and (Test-Path $r) -and ($roots -notcontains $r)) { $roots += $r }
    }
    foreach ($r in $roots) {
        # -Depth 3 reaches PLAT\build_nwy.bat but never descends into PLAT\tools.
        $hit = Get-ChildItem -Path $r -Filter build_nwy.bat -Recurse -Depth 3 -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { $PLAT = $hit.DirectoryName; break }
    }
}
if (-not $PLAT -or -not (Test-Path (Join-Path $PLAT 'build_nwy.bat'))) {
    throw 'build_nwy.bat not found - pass -PLAT explicitly'
}

if ($Mode -eq 'firmware' -and -not $Project) {
    throw 'firmware mode requires -Project <nwy_project dir name>'
}

# Temp files live in %TEMP% - NEVER inside the PLAT tree (SKILL.md pitfall 3).
$wk = Join-Path $env:TEMP 'ec626_skill_build'
New-Item -ItemType Directory -Force -Path $wk | Out-Null

# First input line selects the menu action; many E lines are fallback so the
# looping menu can exit even after stdin drift (SKILL.md pitfall 1).
switch ($Mode) {
    'firmware' {
        # Menu index = alphabetical order of nwy_project dirs, computed now
        # (pitfall 9 - the set of dirs differs per EC626 branch).
        $names = @((Get-ChildItem "$PLAT\nwy_project" -Directory | Sort-Object Name) | ForEach-Object { $_.Name })
        $idx = [array]::IndexOf([string[]]$names, $Project)
        if ($idx -lt 0) {
            throw ("project not found on this branch: $Project`navailable in $PLAT\nwy_project : " + ($names -join ', '))
        }
        $first = "$idx"
    }
    'bootloader' { $first = 'B' }
    'clean'      { $first = 'C' }
    'unilog'     { $first = 'U' }
}

$in  = Join-Path $wk "input_$Mode.txt"
$log = Join-Path $wk "build_$Mode.log"
[System.IO.File]::WriteAllText($in, ("$first`r`n" + ("E`r`n" * 200)), [System.Text.Encoding]::ASCII)
Remove-Item $log -ErrorAction SilentlyContinue

# cmd cannot resolve bare batch names from cwd unless this is cleared (pitfall 4).
Remove-Item Env:\NoDefaultCurrentDirectoryInExePath -ErrorAction SilentlyContinue
[System.Environment]::SetEnvironmentVariable('NoDefaultCurrentDirectoryInExePath', $null, 'Process')
if ($env:NoDefaultCurrentDirectoryInExePath) { throw 'env NoDefaultCurrentDirectoryInExePath not cleared' }

$p = Start-Process cmd -ArgumentList "/c """"$PLAT\build_nwy.bat"" < ""$in"" > ""$log"" 2>&1""" -WorkingDirectory $PLAT -WindowStyle Hidden -PassThru
Start-Process powershell -ArgumentList '-ExecutionPolicy','Bypass','-NoProfile','-File',("`"{0}\scripts\watch_build_log.ps1`"" -f $SkillDir),'-LogPath',$log,'-ProcId',$p.Id
Write-Host "STARTED pid=$($p.Id) mode=$Mode project=$Project in=[$in] log=[$log]"

# Block until the build tree is gone (watchdog kills the menu-loop runaway).
$p.WaitForExit()
Start-Sleep -Seconds 2

$failRe = 'make.*Error|make.*\*\*\*|^fail\s*$|GCCLIB_PATH setting'
$okRe = if ($Mode -eq 'clean') { 'clean all done ok' } else { 'build successfully' }
# Scan the WHOLE log: the looping menu can start another round after success and
# its "Parsing file..." spam pushes the success marker out of any tail window
# (SKILL.md pitfall 7 - this caused a false FAIL with artOk=True).
$ok = @(Select-String -Path $log -Pattern $okRe -ErrorAction SilentlyContinue)
$failed = @(Select-String -Path $log -Pattern $failRe -ErrorAction SilentlyContinue)

# Artifact confirmation so RESULT cannot be a stale banner.
$artOk = $true
if ($Mode -eq 'bootloader') {
    $artOk = Test-Path (Join-Path $PLAT 'gccout\ec626_0h00_ec626\bootloader\bootloader.bin')
} elseif ($Mode -eq 'firmware') {
    $hits = Get-ChildItem (Join-Path $PLAT 'gccout\ec626_0h00_ec626') -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName 'app-demo-flash.bin') }
    $artOk = [bool]$hits
}

if ($ok.Count -gt 0 -and $failed.Count -eq 0 -and $artOk) {
    Remove-Item $in -Force -ErrorAction SilentlyContinue
    Write-Host "RESULT: SUCCESS mode=$Mode project=$Project log=$log"
    exit 0
} else {
    Write-Host "RESULT: FAIL mode=$Mode project=$Project log=$log artOk=$artOk"
    if ($failed.Count -gt 0) { $failed | Select-Object -First 10 | ForEach-Object { Write-Host $_.Line } }
    Write-Host "Full log: $log"
    exit 1
}
