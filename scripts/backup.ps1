# AIX OS — Бэкап данных
# Использование: .\scripts\backup.ps1 [метка]
# Пример: .\scripts\backup.ps1 poc_final

param([string]$Label = "auto")

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$date = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupName = "data_backup_${Label}_${date}"
$backupPath = Join-Path $root $backupName

if (-not (Test-Path "data")) {
    Write-Host "❌ Папка data/ не найдена" -ForegroundColor Red
    exit 1
}

Write-Host "📦 Бэкап: $backupName" -ForegroundColor Cyan
Copy-Item -Path "data" -Destination $backupPath -Recurse -Force

# Также бэкапим код (ключевые файлы)
$codeBackup = Join-Path $backupPath "code"
New-Item -ItemType Directory -Force -Path $codeBackup | Out-Null
Copy-Item "network\server.py" $codeBackup -ErrorAction SilentlyContinue
Copy-Item "cli\main.py" $codeBackup -ErrorAction SilentlyContinue
Copy-Item "web\index.html" $codeBackup -ErrorAction SilentlyContinue

$size = (Get-ChildItem $backupPath -Recurse | Measure-Object -Property Length -Sum).Sum / 1KB
Write-Host "✅ Готово: $backupName ($([math]::Round($size, 1)) KB)" -ForegroundColor Green