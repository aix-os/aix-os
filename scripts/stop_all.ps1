# AIX OS — Остановка всех нод
# Использование: .\scripts\stop_all.ps1

Write-Host "🛑 Останавливаю все ноды AIX OS..." -ForegroundColor Yellow

$procs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and $_.CommandLine -match "network.server|http.server"
}

if ($procs) {
    $procs | Stop-Process -Force
    Write-Host "✅ Остановлено процессов: $($procs.Count)" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Нет запущенных нод" -ForegroundColor Cyan
}