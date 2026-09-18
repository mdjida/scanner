# Backend setup script for Windows.
# Downloads an embedded Python 3.11.9 into the project folder if the system
# Python is not 3.11/3.12, creates a virtual environment, and installs dependencies.

$ErrorActionPreference = "Stop"
$pythonVersion = "3.11.9"
$embedZip = "python-$pythonVersion-embed-amd64.zip"
$embedUrl = "https://www.python.org/ftp/python/$pythonVersion/$embedZip"
$embedDir = "$PSScriptRoot\python_embed"

function Test-UsablePython($pyPath) {
    if (-not $pyPath -or -not (Test-Path $pyPath)) { return $false }
    $version = & $pyPath --version 2>&1
    return $version -match "Python (3\.11|3\.12)\."
}

function Get-EmbedPython {
    [CmdletBinding()]
    param()

    $target = "$embedDir\python.exe"
    if (Test-Path $target) {
        Write-Host "Using existing embedded Python at $embedDir"
        return $target
    }

    Write-Host "Downloading embedded Python $pythonVersion to $embedDir..."
    New-Item -ItemType Directory -Path $embedDir -Force | Out-Null
    $zipPath = "$embedDir\$embedZip"
    Invoke-WebRequest -Uri $embedUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $embedDir -Force
    Remove-Item $zipPath

    # Enable site packages (pip/venv support).
    $pthFile = Get-ChildItem "$embedDir\*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName
        $content = $content -replace "^#import site", "import site"
        Set-Content $pthFile.FullName $content
    }

    # Install pip (suppress output so it doesn't pollute the return value).
    $getPipPath = "$embedDir\get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPipPath -UseBasicParsing
    & "$target" $getPipPath --no-warn-script-location | Out-Null
    Remove-Item $getPipPath

    return $target
}

$usablePython = $null

# Try system Python.
if (Get-Command python -ErrorAction SilentlyContinue) {
    $candidate = & python -c "import sys; print(sys.executable)" 2>&1
    if (Test-UsablePython $candidate) {
        $usablePython = $candidate
        Write-Host "Using system Python: $usablePython"
    }
}

# Use embedded Python if no usable system Python found.
if (-not $usablePython) {
    $usablePython = Get-EmbedPython
}

# Create venv.
$venvDir = "$PSScriptRoot\venv"
if (Test-Path $venvDir) {
    Write-Host "Removing existing venv..."
    Remove-Item -Recurse -Force $venvDir
}

Write-Host "Creating virtual environment..."
# Embedded Python does not include venv by default; use virtualenv.
& $usablePython -m pip install virtualenv --no-warn-script-location | Out-Null
& $usablePython -m virtualenv $venvDir | Out-Null
$venvPython = "$venvDir\Scripts\python.exe"

# Upgrade pip and install requirements.
Write-Host "Installing dependencies (this may take a few minutes)..."
& $venvPython -m pip install --upgrade pip | Out-Null
& $venvPython -m pip install -r "$PSScriptRoot\requirements.txt"

Write-Host "Setup complete."
Write-Host "Activate with: venv\Scripts\Activate.ps1"
Write-Host "Run server:    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Write-Host "Ingest cards:  python cli.py 3"
