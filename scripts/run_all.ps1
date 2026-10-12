# AIX OS - Run all nodes (A, B, Web) + auto-generate AI_BRIEF.md
# Usage: .\scripts\run_all.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  AIX OS - Starting network" -ForegroundColor Yellow
Write-Host "===========================================" -ForegroundColor Cyan

if (-not (Test-Path "network\server.py")) {
    Write-Host "ERROR: network\server.py not found. Run from AIX-OS root." -ForegroundColor Red
    exit 1
}

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "ERROR: venv not found at .venv\Scripts\python.exe" -ForegroundColor Red
    exit 1
}

# --- Auto-generate AI_BRIEF.md before start ---
Write-Host ""
Write-Host "[0/3] Regenerating AI_BRIEF.md..." -ForegroundColor Magenta
try {
    & $py scripts\ai_brief.py --output AI_BRIEF.md
} catch {
    Write-Host "  (AI_BRIEF.md generation skipped)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[1/3] Node A (:8010)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; & '$py' -m network.server --port 8010 --url http://127.0.0.1:8010 --data data/chain_A.json"

Start-Sleep -Seconds 3

Write-Host "[2/3] Node B (:8011)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; & '$py' -m network.server --port 8011 --url http://127.0.0.1:8011 --data data/chain_B.json"

Start-Sleep -Seconds 3

Write-Host "[3/3] Web Wallet (:9000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\web'; & '$py' -m http.server 9000"

Write-Host ""
Write-Host "OK. All started." -ForegroundColor Green
Write-Host "  Node A:  http://localhost:8010" -ForegroundColor Cyan
Write-Host "  Node B:  http://localhost:8011" -ForegroundColor Cyan
Write-Host "  Web UI:  http://localhost:9000" -ForegroundColor Cyan
Write-Host ""
Write-Host "AI_BRIEF.md: $root\AI_BRIEF.md" -ForegroundColor Magenta
Write-Host "Stop all: .\scripts\stop_all.ps1" -ForegroundColor Yellow