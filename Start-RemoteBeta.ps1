param(
    [ValidateRange(1024,65535)][int]$ApiPort = 8481
)
$ErrorActionPreference = 'Stop'
$bioRoot = $PSScriptRoot
$bioPython = Join-Path $bioRoot 'backend/.venv/Scripts/python.exe'
$bioTunnel = Join-Path $bioRoot 'backend/data/tools/cloudflared.exe'
$bioData = Join-Path $bioRoot 'backend/data/remote-beta'
$bioDist = Join-Path $bioRoot 'mobile/.beta-dist'
if (-not (Test-Path -LiteralPath $bioPython)) { throw 'Prepare the backend environment first; see README.md.' }
if (-not (Test-Path -LiteralPath $bioTunnel)) { throw 'Install the official Windows cloudflared utility at backend/data/tools/cloudflared.exe first.' }
if (-not (Test-Path -LiteralPath (Join-Path $bioDist 'index.html'))) { throw 'Export the private beta web app into mobile/.beta-dist first.' }
$bioProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$ApiPort)
try { $bioProbe.ExclusiveAddressUse=$true; $bioProbe.Start() }
catch { throw "Port $ApiPort is occupied. Keep the existing server running or choose -ApiPort with a free port." }
finally { $bioProbe.Stop() }
New-Item -ItemType Directory -Force -Path $bioData | Out-Null
$bioSaved = @{}
foreach ($bioKey in @('BIOGUARD_PRIVATE_BETA','BIOGUARD_DATA_DIR','BIOGUARD_WEB_DIR','BIOGUARD_SECURE_COOKIES','BIOGUARD_CORS_ORIGINS')) { $bioSaved[$bioKey]=[Environment]::GetEnvironmentVariable($bioKey,'Process') }
$bioApiProcess=$null
$bioTunnelProcess=$null
try {
    $env:BIOGUARD_PRIVATE_BETA='1'
    $env:BIOGUARD_DATA_DIR=$bioData
    $env:BIOGUARD_WEB_DIR=$bioDist
    $env:BIOGUARD_SECURE_COOKIES='1'
    $env:BIOGUARD_CORS_ORIGINS=''
    $bioApiProcess=Start-Process -FilePath $bioPython -ArgumentList @('-m','uvicorn','app:app','--app-dir','backend','--host','127.0.0.1','--port',"$ApiPort",'--no-access-log') -WorkingDirectory $bioRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $bioData 'server-output.log') -RedirectStandardError (Join-Path $bioData 'server-error.log') -PassThru
    $bioReady=$false
    for ($bioAttempt=0; $bioAttempt -lt 120; $bioAttempt++) {
        if ($bioApiProcess.HasExited) { throw 'The beta server stopped. Check backend/data/remote-beta/server-error.log.' }
        try {
            $bioHealth=Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/health" -TimeoutSec 2
            if ($bioHealth.private_beta -ne $true -or $bioHealth.identification_available -ne $true) { throw 'The beta model is not ready.' }
            $bioReady=$true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $bioReady) { throw 'Timed out waiting for the beta model. Check server-error.log.' }
    $bioTunnelProcess=Start-Process -FilePath $bioTunnel -ArgumentList @('tunnel','--url',"http://127.0.0.1:$ApiPort",'--no-autoupdate','--protocol','http2') -WorkingDirectory $bioRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $bioData 'tunnel-output.log') -RedirectStandardError (Join-Path $bioData 'tunnel-error.log') -PassThru
    $bioUrl=$null
    for ($bioAttempt=0; $bioAttempt -lt 90; $bioAttempt++) {
        if ($bioTunnelProcess.HasExited) { throw 'The remote link stopped. Check backend/data/remote-beta/tunnel-error.log.' }
        $bioLog=Get-Content -LiteralPath (Join-Path $bioData 'tunnel-error.log') -Raw -ErrorAction SilentlyContinue
        if ($bioLog -match 'https://[a-z0-9-]+\.trycloudflare\.com') { $bioUrl=$Matches[0]; break }
        Start-Sleep -Seconds 1
    }
    if (-not $bioUrl) { throw 'No test URL was issued. Check tunnel-error.log.' }
    [System.IO.File]::WriteAllText((Join-Path $bioData 'active-url.txt'),$bioUrl,[System.Text.UTF8Encoding]::new($false))
    [pscustomobject]@{url=$bioUrl;api_port=$ApiPort;tunnel_pid=$bioTunnelProcess.Id;tunnel_started_at=$bioTunnelProcess.StartTime.ToUniversalTime().ToString('o');started_at=[DateTimeOffset]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $bioData 'active-session.json') -Encoding UTF8
    Write-Host "BioGuard remote beta: $bioUrl"
    Write-Host 'This uses separate remote-beta data. Existing local reports are untouched.'
    Write-Host 'Test logins: grounds / 123, ecology / 123, management / 123.'
    Write-Host 'Keep this terminal and laptop running. Ctrl+C stops this remote beta.'
    Write-Host 'A restart creates a different URL: an APK built with the previous URL needs a new build.'
    while (-not $bioTunnelProcess.HasExited) {
        if ($bioApiProcess.HasExited) { throw 'The beta server stopped. Check server-error.log.' }
        Start-Sleep -Seconds 2
    }
    throw 'The remote link stopped. Check tunnel-error.log.'
} finally {
    if ($bioTunnelProcess -and -not $bioTunnelProcess.HasExited) { Stop-Process -Id $bioTunnelProcess.Id -ErrorAction SilentlyContinue }
    if ($bioApiProcess -and -not $bioApiProcess.HasExited) {
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$($bioApiProcess.Id)" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*uvicorn app:app*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
        Stop-Process -Id $bioApiProcess.Id -ErrorAction SilentlyContinue
    }
    foreach ($bioKey in $bioSaved.Keys) { [Environment]::SetEnvironmentVariable($bioKey,$bioSaved[$bioKey],'Process') }
}
