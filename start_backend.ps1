# One-click backend launcher for mobile / Android testing.
# Binds to 0.0.0.0 so Android on the same Wi-Fi can reach it.
# Also opens Windows Firewall port 8000 for private networks when run as admin.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "backend"
Set-Location $backendDir

function Ensure-FirewallRule {
    try {
        $rule = Get-NetFirewallRule -DisplayName "Live Comp Backend" -ErrorAction SilentlyContinue
        if (-not $rule) {
            New-NetFirewallRule `
                -DisplayName "Live Comp Backend" `
                -Direction Inbound `
                -LocalPort 8000 `
                -Protocol TCP `
                -Action Allow `
                -Profile Private,Domain `
                -ErrorAction Stop | Out-Null
            Write-Host "Firewall rule added for port 8000 (private/domain networks)." -ForegroundColor Green
        } else {
            Write-Host "Firewall rule already present." -ForegroundColor DarkGray
        }
    } catch {
        Write-Host "Could not auto-configure firewall (requires admin)." -ForegroundColor Yellow
        Write-Host "If your phone cannot connect, run this script as Administrator once." -ForegroundColor Yellow
    }
}

Ensure-FirewallRule

.\venv\Scripts\Activate.ps1
$env:HOST = "0.0.0.0"
$env:LCO_UNLOAD_OCR_AFTER_SCAN = "1"

Write-Host "Starting Live Comp backend..." -ForegroundColor Cyan
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
