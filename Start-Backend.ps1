$ErrorActionPreference = 'Stop'
$bioBackend = Join-Path $PSScriptRoot 'backend'
$bioPython = Join-Path $bioBackend '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $bioPython)) {
    throw 'Backend environment is missing. Follow the setup steps in README.md.'
}
Push-Location -LiteralPath $bioBackend
try {
    if (-not (Test-Path -LiteralPath (Join-Path $bioBackend 'model\bioguard.keras'))) {
        & $bioPython setup_model.py
        if ($LASTEXITCODE -ne 0) { throw 'Model extraction failed.' }
    }
    Write-Host 'Starting BioGuard. Keep this window running while testing.'
    & $bioPython -m uvicorn app:app --host 0.0.0.0 --port 8000 --no-access-log
} finally { Pop-Location }
