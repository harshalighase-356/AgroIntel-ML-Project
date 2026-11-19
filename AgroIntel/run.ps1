$ErrorActionPreference = "Stop"

$pythonExecutable = Join-Path $env:LOCALAPPDATA "AgroIntel\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw "AgroIntel's environment was not found. Run .\setup.ps1 first."
}

# Streamlit resolves multipage scripts from the current directory. Always use
# the project directory even when this script is launched from another folder.
Set-Location -LiteralPath $PSScriptRoot
& $pythonExecutable -m streamlit run (Join-Path $PSScriptRoot "app.py")
