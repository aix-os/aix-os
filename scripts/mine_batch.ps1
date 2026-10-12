# AIX OS — Пакетный майнинг
# Использование: .\scripts\mine_batch.ps1 <кошелёк> <количество>
# Пример: .\scripts\mine_batch.ps1 alice 50

param(
    [Parameter(Mandatory=$true)][string]$Wallet,
    [Parameter(Mandatory=$true)][int]$Count,
    [string]$Node = "http://localhost:8010"
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "⛏️  Майню $Count блоков для '$Wallet'..." -ForegroundColor Cyan
Write-Host "   Нода: $Node" -ForegroundColor Gray
Write-Host ""

$start = Get-Date
$mined = 0
$lottery = 0

for ($i = 1; $i -le $Count; $i++) {
    $output = python cli/main.py node --node $Node mine $Wallet 2>&1
    if ($output -match "✅ Блок") {
        $mined++
    }
    if ($output -match "СЧАСТЛИВЫЙ БЛОК") {
        $lottery++
    }
    # Прогресс каждые 10 блоков
    if ($i % 10 -eq 0 -or $i -eq $Count) {
        $elapsed = (Get-Date) - $start
        Write-Host "   [$i/$Count] Замайнено: $mined, лотерей: $lottery, время: $($elapsed.TotalSeconds.ToString('F1'))с" -ForegroundColor Green
    }
}

$elapsed = (Get-Date) - $start
$reward = $mined * 50
$prize = $lottery * 100

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ✅ Готово!" -ForegroundColor Green
Write-Host "  Блоков:      $mined" -ForegroundColor Yellow
Write-Host "  Награда:     +$reward AIX" -ForegroundColor Yellow
Write-Host "  Лотерей:     $lottery (сумма: +$prize AIX)" -ForegroundColor Magenta
Write-Host "  Всего:       +$($reward + $prize) AIX" -ForegroundColor Cyan
Write-Host "  Время:       $($elapsed.TotalSeconds.ToString('F1'))с" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan