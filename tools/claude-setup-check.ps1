# Claude 스킬·MCP·플러그인 점검표 생성 (Windows PowerShell 5.1 이상)
# 실행: powershell -ExecutionPolicy Bypass -File .\claude-setup-check.ps1
# 결과: 바탕화면에 "Claude_점검표_<컴퓨터이름>.md" 생성 + 화면 출력
# 읽기만 하며 아무것도 설치·삭제·변경하지 않는다. API 키 파일은 내용을 읽지 않고 있는지만 본다.

$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# claude.ai 계정에 등록되어 있어 어느 컴퓨터에서든 동기화되는 스킬(2026-10-25 클라우드 세션에서 확인)
$AccountSkills = @(
  'academic-pptx','brand-guidelines','built-in-browser','canvas-design','chrome-browser','computer-use',
  'daegu-design-system-deck','daegu-policy-ppt','daegu-report-hwpx','deep-research','design-taste-frontend',
  'docs','docx','excelize-xlsx','gongmunseo','google-workspace','handocsmith','hwpx','hwpx-new',
  'import-memory','kordoc','korean-law','korean-report-hwpx','meka-gwak','ministry-minister-report',
  'morning','pdf','ppt-master','pptx','pptxgenjs','safety-accident-report','seedance-clean',
  'skill-creator','xlsx'
)

$ClaudeDir = Join-Path $env:USERPROFILE '.claude'
$Rows = New-Object System.Collections.Generic.List[object]
function Add-Row($kind, $name, $where, $action) {
  $Rows.Add([pscustomobject]@{ 종류 = $kind; 이름 = $name; 위치 = $where; 다른PC에서할일 = $action })
}

# 1) 노트북 폴더에 직접 넣은 스킬
$SkillDir = Join-Path $ClaudeDir 'skills'
if (Test-Path $SkillDir) {
  Get-ChildItem $SkillDir -Directory | Where-Object { $_.Name -ne 'synced' } | ForEach-Object {
    if (-not (Test-Path (Join-Path $_.FullName 'SKILL.md'))) { return }
    if ($AccountSkills -contains $_.Name) {
      Add-Row '스킬' $_.Name '노트북 폴더 + 계정' '없음(계정에서 동기화). 노트북 사본은 중복이라 지워도 됨'
    } else {
      Add-Row '스킬' $_.Name '노트북에만' 'claude.ai 설정→기능→스킬에 zip 업로드(권장) 또는 폴더 복사'
    }
  }
}
foreach ($s in $AccountSkills) { Add-Row '스킬' $s '계정(claude.ai)' '없음' }

# 2) Claude Code MCP
$claude = Get-Command claude
if ($claude) {
  $mcp = & claude mcp list 2>$null
  foreach ($line in $mcp) {
    if ($line -notmatch '^(.+?):\s+(.+?)\s+-\s+(.+)$') { continue }
    $name = $Matches[1].Trim(); $state = $Matches[3].Trim()
    if ($name -like 'claude.ai *') {
      Add-Row 'MCP' $name "계정 커넥터 ($state)" '없음(새 PC 첫 사용 때 재로그인 필요할 수 있음)'
    } elseif ($name -like 'plugin:*') {
      Add-Row 'MCP' $name "플러그인 포함 ($state)" '해당 플러그인 따라감(아래 플러그인 행 참고)'
    } else {
      Add-Row 'MCP' $name "노트북에만 ($state)" 'claude mcp add 로 다시 등록 또는 claude.ai 커넥터로 전환'
    }
  }

  # 3) Claude Code 플러그인
  $plug = & claude plugin list 2>$null
  foreach ($line in $plug) {
    if ($line -notmatch '^\s*>\s*(\S+)@(\S+)') { continue }
    $p = $Matches[1]; $m = $Matches[2]
    if ($m -eq 'synced') {
      Add-Row '플러그인' "$p@$m" '계정(claude.ai)' '없음'
    } elseif ($m -eq 'wsof11') {
      Add-Row '플러그인' "$p@$m" '노트북 설치 + GitHub 저장소' 'wsof11 저장소를 받아 Claude Code로 열기(자동 활성화) 또는 /plugin install'
    } else {
      Add-Row '플러그인' "$p@$m" '노트북에만' "/plugin marketplace add <$m 주소> → /plugin install $p@$m"
    }
  }
} else {
  Add-Row 'Claude Code' 'claude 명령' '설치 안 됨' 'Claude Code CLI 설치 후 다시 점검'
}

# 4) Claude 데스크톱 앱 MCP 설정(노트북 로컬 파일)
$Desktop = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
if (Test-Path $Desktop) {
  $cfg = Get-Content $Desktop -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($cfg.mcpServers) {
    $cfg.mcpServers.PSObject.Properties | ForEach-Object {
      Add-Row 'MCP(데스크톱 앱)' $_.Name '노트북에만' 'claude_desktop_config.json 복사 또는 다시 등록'
    }
  }
}

# 5) Python 패키지(스킬 실행에 필요)
$py = (Get-Command py) ; if (-not $py) { $py = Get-Command python }
foreach ($pkg in 'python-docx','kiwipiepy','kiwipiepy_model','pypdf') {
  if ($py) { & $py.Source -m pip show $pkg 2>$null | Out-Null; $ok = ($LASTEXITCODE -eq 0) } else { $ok = $false }
  if ($ok) { Add-Row 'Python 패키지' $pkg '노트북에만 (설치됨)' "python -m pip install --use-pep517 $pkg" }
  else { Add-Row 'Python 패키지' $pkg '설치 안 됨' '필요한 스킬을 쓸 때 설치' }
}

# 6) 로컬에 저장된 키·자격증명(내용은 읽지 않음)
$keyPaths = @(
  @{ n = 'lawfirm 작업폴더·법제처 키'; p = (Join-Path $env:LOCALAPPDATA 'intent-brief') },
  @{ n = 'lawfirm 작업폴더(대체 경로)'; p = (Join-Path $env:USERPROFILE '.intent-brief') },
  @{ n = '빅케이스 설정'; p = (Join-Path $env:USERPROFILE '.case-search') }
)
foreach ($k in $keyPaths) {
  if (Test-Path $k.p) { Add-Row '키·자격증명' $k.n "노트북에만 ($($k.p))" '/lawfirm:law-key-setup 등으로 다시 등록' }
}

# 출력
$sorted = $Rows | Sort-Object 종류, 이름, 위치 -Unique | Sort-Object @{ Expression = { if ($_.위치 -like '노트북에만*') { 0 } elseif ($_.위치 -like '*노트북*') { 1 } else { 2 } } }, 종류, 이름
$local = @($sorted | Where-Object { $_.위치 -like '노트북에만*' }).Count

$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# Claude 환경 점검표 — $env:COMPUTERNAME")
[void]$md.AppendLine('')
[void]$md.AppendLine("- 점검 일시: $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
[void]$md.AppendLine("- 다른 컴퓨터에서 다시 설치해야 할 항목(노트북에만): **$local 개**")
[void]$md.AppendLine('- 「계정」 항목은 같은 계정으로 로그인하면 자동으로 따라온다.')
[void]$md.AppendLine('')
[void]$md.AppendLine('| 확인 | 종류 | 이름 | 위치 | 다른 PC에서 할 일 |')
[void]$md.AppendLine('|---|---|---|---|---|')
foreach ($r in $sorted) {
  $box = if ($r.위치 -like '노트북에만*') { '☐' } else { '✅' }
  [void]$md.AppendLine("| $box | $($r.종류) | $($r.이름) | $($r.위치) | $($r.다른PC에서할일) |")
}

$out = Join-Path ([Environment]::GetFolderPath('Desktop')) "Claude_점검표_$env:COMPUTERNAME.md"
[System.IO.File]::WriteAllText($out, $md.ToString(), (New-Object System.Text.UTF8Encoding $true))
$sorted | Format-Table -AutoSize -Wrap
Write-Host ''
Write-Host "다른 PC에서 다시 설치할 항목: $local 개"
Write-Host "점검표 저장: $out"
