$ErrorActionPreference = 'Stop'
$bioPython = Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'
& $bioPython (Join-Path $PSScriptRoot 'backend\preview_mobile.py')
