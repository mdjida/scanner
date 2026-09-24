# One-click backend launcher for mobile / Android testing.
# Binds to 0.0.0.0 so Android on the same Wi-Fi can reach it.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "backend"
Set-Location $backendDir

.\venv\Scripts\Activate.ps1
$env:HOST = "0.0.0.0"
$env:LCO_UNLOAD_OCR_AFTER_SCAN = "1"

Write-Host "Starting Live Comp backend..." -ForegroundColor Cyan
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
