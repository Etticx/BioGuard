[CmdletBinding(SupportsShouldProcess)]
param()
$ErrorActionPreference='Stop'
$bioStatePath=Join-Path $PSScriptRoot 'backend/data/remote-beta/active-session.json'
if (-not (Test-Path -LiteralPath $bioStatePath)) { throw 'No remote beta session was recorded.' }
$bioState=Get-Content -LiteralPath $bioStatePath -Raw | ConvertFrom-Json
if (-not $bioState.tunnel_pid -or -not $bioState.tunnel_started_at) { throw 'Session ownership information is unavailable. Stop the original remote beta terminal instead.' }
$bioProcess=Get-Process -Id $bioState.tunnel_pid -ErrorAction SilentlyContinue
if (-not $bioProcess) { Write-Host 'The recorded remote beta tunnel has already stopped.'; return }
$bioExpected=[System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'backend/data/tools/cloudflared.exe'))
$bioStarted=([DateTimeOffset]$bioState.tunnel_started_at).UtcDateTime
if ($bioProcess.Path -ne $bioExpected -or [Math]::Abs(($bioProcess.StartTime.ToUniversalTime()-$bioStarted).TotalMilliseconds) -gt 1) { throw 'The process does not match the recorded beta tunnel. Nothing was stopped.' }
if ($PSCmdlet.ShouldProcess('The recorded BioGuard remote beta tunnel','Stop')) {
    Stop-Process -InputObject $bioProcess
    Write-Host 'Stopped the beta link. Its launcher will also stop its own server.'
}
