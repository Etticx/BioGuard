$ErrorActionPreference = 'Stop'
$bioMobile = Join-Path $PSScriptRoot 'mobile'
# Prefer the current bundled runtime when present; it satisfies Expo's Node requirement.
$bioBundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$bioNode = if (Test-Path -LiteralPath $bioBundledNode) { $bioBundledNode } else { 'node' }
Push-Location -LiteralPath $bioMobile
try {
    Write-Host 'Use the same Wi-Fi on the phone and laptop. Open the QR code with Expo Go.'
    & $bioNode '.\node_modules\expo\bin\cli' start --offline
} finally { Pop-Location }

