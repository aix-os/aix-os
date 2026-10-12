# AIX OS - Stop all nodes + regenerate AI_BRIEF.md
# Usage: .\scripts\stop_all.ps1

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Stopping all AIX OS nodes..." -ForegroundColor Yellow

$found = 0

$servers = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "network.server|http.server" }

foreach ($p in $servers) {
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        $found++
    } catch {
        Write-Host "  Could not kill PID $($p.ProcessId)" -ForegroundColor Red
    }
}

if ($found -gt 0) {
    Write-Host "Stopped processes: $found" -ForegroundColor Green
} else {
    Write-Host "No running nodes found" -ForegroundColor Cyan
}

# --- Regenerate AI_BRIEF.md after stop ---
$py = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $py) {
    Write-Host ""
    Write-Host "Regenerating AI_BRIEF.md..." -ForegroundColor Magenta
    try {
        & $py scripts\ai_brief.py --output AI_BRIEF.md
    } catch {
        Write-Host "  (skipped)" -ForegroundColor Yellow
    }
}