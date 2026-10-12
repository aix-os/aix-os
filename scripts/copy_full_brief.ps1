# AIX OS - Pack full brief + copy short version to clipboard
# Usage: .\scripts\copy_full_brief.ps1

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "ERROR: venv not found" -ForegroundColor Red
    exit 1
}

Write-Host "Packing full brief..." -ForegroundColor Cyan
& $py scripts\pack_for_ai.py --output AI_BRIEF_FULL.md --core

$shortPath = Join-Path $root "AI_BRIEF.md"
$header = "Partner, read AI_BRIEF.md. Next: DAO in core/governance/dao.py." + [Environment]::NewLine
$header += "Full project pack: AI_BRIEF_FULL.md (attach as file)." + [Environment]::NewLine + [Environment]::NewLine
$content = Get-Content $shortPath -Raw -Encoding UTF8
Set-Clipboard -Value ($header + $content)

$fullPath = Join-Path $root "AI_BRIEF_FULL.md"
$fullSize = (Get-Item $fullPath).Length / 1KB

Write-Host ""
Write-Host "OK." -ForegroundColor Green
Write-Host "  AI_BRIEF.md (short)  -> clipboard" -ForegroundColor Yellow
Write-Host "  AI_BRIEF_FULL.md     -> $([math]::Round($fullSize,1)) KB on disk" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  1. Open new chat" -ForegroundColor White
Write-Host "  2. Ctrl+V (short brief)" -ForegroundColor White
Write-Host "  3. Attach AI_BRIEF_FULL.md as a file" -ForegroundColor White