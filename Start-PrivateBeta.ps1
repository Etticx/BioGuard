param(
    [ValidateSet('Web','Expo')][string]$Mode = 'Web',
    [ValidateRange(1024,65535)][int]$ApiPort = 8001,
    [ValidateRange(1024,65535)][int]$ExpoPort = 8383
)
$ErrorActionPreference = 'Stop'
$bioRoot = $PSScriptRoot
$bioMobile = Join-Path $bioRoot 'mobile'
$bioPython = Join-Path $bioRoot 'backend/.venv/Scripts/python.exe'
$bioBundledNode = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$bioNode = if (Test-Path -LiteralPath $bioBundledNode) { $bioBundledNode } else { (Get-Command node).Source }
$bioVersion = (& $bioNode --version).TrimStart('v') -as [version]
if ($bioVersion -lt [version]'22.13.0') { throw 'Use Node 24 LTS (or Node 22.13+) to run this beta.' }
if (-not (Test-Path -LiteralPath $bioPython)) { throw 'Prepare backend/.venv using README.md first.' }
if ([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners().Port -contains $ApiPort) { throw "Port $ApiPort is already running. Stop that beta or choose another -ApiPort." }
if ($Mode -eq 'Expo') {
    $bioProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any,$ExpoPort)
    try { $bioProbe.Start() } catch { throw "Port $ExpoPort is occupied or reserved by Windows. Choose another -ExpoPort." } finally { $bioProbe.Stop() }
}
$bioData = Join-Path $bioRoot 'backend/data/private-beta'
$bioDist = Join-Path $bioMobile '.beta-dist'
$bioSaved = @{}
foreach ($bioKey in @('BIOGUARD_PRIVATE_BETA','BIOGUARD_DATA_DIR','BIOGUARD_WEB_DIR','BIOGUARD_SECURE_COOKIES','BIOGUARD_CORS_ORIGINS','EXPO_PUBLIC_PRIVATE_BETA','EXPO_PUBLIC_API_URL')) { $bioSaved[$bioKey] = [Environment]::GetEnvironmentVariable($bioKey,'Process') }
$bioApiProcess = $null
Push-Location -LiteralPath $bioRoot
try {
    $env:BIOGUARD_PRIVATE_BETA = '1'
    $env:BIOGUARD_DATA_DIR = $bioData
    $env:BIOGUARD_WEB_DIR = $bioDist
    $env:BIOGUARD_SECURE_COOKIES = '0' # Local Wi-Fi only. Hosted builds use HTTPS and secure cookies.
    $env:BIOGUARD_CORS_ORIGINS = ''
    $env:EXPO_PUBLIC_PRIVATE_BETA = '1'
    $env:EXPO_PUBLIC_API_URL = '/'
    New-Item -ItemType Directory -Force -Path $bioData | Out-Null
    Push-Location -LiteralPath $bioMobile
    try {
        & $bioNode node_modules/expo/bin/cli export --platform web --clear --output-dir .beta-dist
        if ($LASTEXITCODE -ne 0) { throw 'Beta web build failed.' }
    } finally { Pop-Location }
    $bioAddress = 'YOUR_LAPTOP_IP'
    try {
        $bioRoutes = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric
        foreach ($bioRoute in $bioRoutes) {
            $bioCandidate = Get-NetIPAddress -InterfaceIndex $bioRoute.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)' } | Select-Object -First 1
            if ($bioCandidate) { $bioAddress = $bioCandidate.IPAddress; break }
        }
    } catch { }
    Write-Host 'BioGuard private beta - local Wi-Fi only; nothing is published.'
    Write-Host "Phone browser: http://${bioAddress}:$ApiPort/"
    Write-Host "Ecology desk: http://${bioAddress}:$ApiPort/officer"
    Write-Host 'Initial access is in backend/data/private-beta/local-accounts.json. Change temporary passwords before inviting testers.'
    Write-Host 'Keep phones and laptop on the same private Wi-Fi. Do not forward this port to the Internet.'
    if ($Mode -eq 'Web') {
        & $bioPython -m uvicorn app:app --app-dir backend --host 0.0.0.0 --port $ApiPort --no-access-log
    } else {
        if ($bioAddress -eq 'YOUR_LAPTOP_IP') { throw 'Could not choose a LAN address. Connect to private Wi-Fi and retry.' }
        $env:BIOGUARD_CORS_ORIGINS = "http://${bioAddress}:$ExpoPort,http://localhost:$ExpoPort"
        $bioApiProcess = Start-Process -FilePath $bioPython -ArgumentList @('-m','uvicorn','app:app','--app-dir','backend','--host','0.0.0.0','--port',"$ApiPort",'--no-access-log') -WorkingDirectory $bioRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $bioData 'api-output.log') -RedirectStandardError (Join-Path $bioData 'api-error.log') -PassThru
        $env:EXPO_PUBLIC_API_URL = "http://${bioAddress}:$ApiPort"
        Write-Host 'Install the matching Expo Go on both phones. For iPhone, sign in to Expo on this laptop and the phone using the same account.'
        Push-Location -LiteralPath $bioMobile
        try {
            & $bioNode node_modules/expo/bin/cli start --go --lan --clear --port $ExpoPort
            if ($LASTEXITCODE -ne 0) { throw 'Expo could not start. Check the message above.' }
        }
        finally { Pop-Location }
    }
} finally {
    if ($bioApiProcess) {
        $bioChildren = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($bioApiProcess.Id)" -ErrorAction SilentlyContinue
        foreach ($bioChild in $bioChildren) { if ($bioChild.CommandLine -like '*uvicorn app:app*') { Stop-Process -Id $bioChild.ProcessId -ErrorAction SilentlyContinue } }
        Stop-Process -Id $bioApiProcess.Id -ErrorAction SilentlyContinue
    }
    foreach ($bioKey in $bioSaved.Keys) { [Environment]::SetEnvironmentVariable($bioKey,$bioSaved[$bioKey],'Process') }
    Pop-Location
}
