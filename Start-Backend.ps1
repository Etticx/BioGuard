$ErrorActionPreference = 'Stop'
$bioBackend = Join-Path $PSScriptRoot 'backend'
$bioPython = Join-Path $bioBackend '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $bioPython)) {
    throw 'Backend environment is missing. Follow the setup steps in README.md.'
}
$bioPreviousModelDisabled = $env:BIOGUARD_MODEL_DISABLED
Push-Location -LiteralPath $bioBackend
try {
    & $bioPython setup_model.py
    if ($LASTEXITCODE -ne 0) {
        $env:BIOGUARD_MODEL_DISABLED = '1'
        Write-Warning 'Identification could not be prepared. Staff reporting will still start.'
    }
    Write-Host 'Starting BioGuard. Keep this window running while testing.'
    & $bioPython -m uvicorn app:app --host 0.0.0.0 --port 8000 --no-access-log
} finally { $env:BIOGUARD_MODEL_DISABLED = $bioPreviousModelDisabled; Pop-Location }
