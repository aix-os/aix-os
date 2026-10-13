# Install promo dependencies (ASCII only for PS 5.1)
Write-Host "Installing promo dependencies..." -ForegroundColor Cyan

$python = ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "ERROR: .venv not found. Run from project root." -ForegroundColor Red
    exit 1
}

& $python -m pip install --upgrade pip
& $python -m pip install imageio imageio-ffmpeg pillow numpy

Write-Host ""
Write-Host "Done. Now run:" -ForegroundColor Green
Write-Host "  .venv\Scripts\python.exe scripts\make_promo.py" -ForegroundColor Yellow