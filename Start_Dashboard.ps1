$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$localPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$sessionPython = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'work\.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $localPython) {
    $dashboardPython = $localPython
} elseif (Test-Path -LiteralPath $sessionPython) {
    $dashboardPython = $sessionPython
} else {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required. Install it and rerun.' }
    & $localPython -m pip install -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    $dashboardPython = $localPython
}
& $dashboardPython -m streamlit run app\streamlit_app.py
