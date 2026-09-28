# ===== AICom 团队技能一键安装 =====
# 仓库: mengxiangrui1211/NEOWAY-SKILLS-REPO
# 由 AICom 发布技能时自动维护; 运行时从 api.github.com 拉取最新 skills-index.json
# 重跑同一行 = 增量更新(同版本跳过, 新版本覆盖)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
$Repo = 'mengxiangrui1211/NEOWAY-SKILLS-REPO'
$defTarget = Join-Path $env:USERPROFILE '.claude\skills'
$in = Read-Host ('目标技能目录(直接回车 = ' + $defTarget + ')')
$TargetDir = if ($in) { $in } else { $defTarget }

$H = @{ 'User-Agent' = 'AICom-TeamSkills' }
$idxUrl = 'https://api.github.com/repos/' + $Repo + '/contents/skills-index.json'
try {
  $idx = Invoke-RestMethod -Uri $idxUrl -Headers $H
} catch {
  $t = Read-Host '拉取索引失败(私有仓库?): 粘贴 GitHub 访问令牌后重试, 直接回车退出'
  if (-not $t) { throw }
  $H.Authorization = 'Bearer ' + $t
  $idx = Invoke-RestMethod -Uri $idxUrl -Headers $H
}
$text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(($idx.content -replace '\s', '')))
$Skills = ($text | ConvertFrom-Json).skills.PSObject.Properties

if (-not (Test-Path $TargetDir)) { New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null }
$done = @(); $skip = @(); $fail = @()
foreach ($p in $Skills) {
  $s = $p.Value
  $name = $s.name
  if (-not $name -or -not $s.asset) { continue }
  $dest = Join-Path $TargetDir $name
  try {
    $skipIt = $false
    if (Test-Path (Join-Path $dest 'skill.json')) {
      try { if (((Get-Content (Join-Path $dest 'skill.json') -Raw | ConvertFrom-Json).version) -eq $s.version) { $skipIt = $true } } catch {}
    }
    if ($skipIt) { $skip += $name; continue }
    $zip = Join-Path $env:TEMP ($name + '.zip')
    Invoke-WebRequest -Uri $s.asset -OutFile $zip -Headers $H -UseBasicParsing
    $ex = Join-Path $env:TEMP ('aicom-skills-' + $name)
    if (Test-Path $ex) { Remove-Item $ex -Recurse -Force }
    Expand-Archive -Path $zip -DestinationPath $ex -Force -ErrorAction Stop
    $src = Join-Path $ex $name
    if (-not (Test-Path $src)) { $src = $ex }
    if (-not (Test-Path (Join-Path $src 'SKILL.md'))) { throw '压缩包中未找到 SKILL.md' }
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Move-Item $src $dest
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    Remove-Item $ex -Recurse -Force -ErrorAction SilentlyContinue
    $done += $name
  } catch { $fail += ($name + ': ' + $_.Exception.Message) }
}
Write-Host ''
Write-Host ('完成: 安装 ' + $done.Count + ' / 跳过 ' + $skip.Count + ' / 失败 ' + $fail.Count + '  目录: ' + $TargetDir) -ForegroundColor Green
if ($done.Count) { Write-Host ('  已安装: ' + ($done -join ', ')) }
if ($skip.Count) { Write-Host ('  已跳过: ' + ($skip -join ', ')) }
if ($fail.Count) { Write-Host ('  失败详情: ' + ($fail -join ' | ')) -ForegroundColor Red }