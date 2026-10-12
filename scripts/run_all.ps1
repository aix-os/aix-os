# AIX OS — Запуск всех нод
# Использование: .\scripts\run_all.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  AIX OS — Запуск сети" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan

# Проверяем, что мы в корне проекта
if (-not (Test-Path "network\server.py")) {
    Write-Host "❌ Не найден network/server.py. Запусти из корня AIX-OS" -ForegroundColor Red
    exit 1
}

# Запускаем ноду A
Write-Host "`n🚀 Запускаю ноду A (:8010)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; python -m network.server --port 8010 --data data/chain_A.json"

Start-Sleep -Seconds 2

# Запускаем ноду B
Write-Host "🚀 Запускаю ноду B (:8011)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; python -m network.server --port 8011 --data data/chain_B.json"

Start-Sleep -Seconds 2

# Запускаем Web-кошелёк
Write-Host "🌐 Запускаю Web Wallet (:9000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\web'; python -m http.server 9000"

Write-Host "`n✅ Всё запущено!" -ForegroundColor Green
Write-Host "   Нода A:  http://localhost:8010" -ForegroundColor Cyan
Write-Host "   Нода B:  http://localhost:8011" -ForegroundColor Cyan
Write-Host "   Web UI:  http://localhost:9000" -ForegroundColor Cyan
Write-Host "`nОстановить всё: .\scripts\stop_all.ps1" -ForegroundColor Yellow