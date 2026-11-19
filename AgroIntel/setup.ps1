$ErrorActionPreference = "Stop"

$environmentDirectory = Join-Path $env:LOCALAPPDATA "AgroIntel\venv"
$pythonExecutable = Join-Path $environmentDirectory "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    py -m venv $environmentDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Python could not create the virtual environment at $environmentDirectory."
    }
}

& $pythonExecutable -m ensurepip --upgrade
if ($LASTEXITCODE -ne 0) {
    throw "Could not install pip into $environmentDirectory."
}

& $pythonExecutable -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed. Check your internet connection and rerun .\setup.ps1."
}

Write-Host "AgroIntel setup is ready. Start the app with .\run.ps1"
