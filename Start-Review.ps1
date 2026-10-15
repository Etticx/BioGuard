$ErrorActionPreference = 'Stop'
$bioReview = Join-Path $PSScriptRoot 'review'
$bioPython = Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'
Write-Host 'BioGuard photo review: http://localhost:8084'
Write-Host 'Keep this terminal running while reviewing.'
& $bioPython -m http.server 8084 --bind 127.0.0.1 --directory $bioReview
