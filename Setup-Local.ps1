# One-time Windows preparation. Run from the BioGuard folder in PowerShell.
$ErrorActionPreference='Stop'
$bioRoot=$PSScriptRoot
foreach($bioFile in @('backend/requirements.txt','backend/records.py','mobile/package.json','mobile/package-lock.json','mobile/src/app/_layout.tsx','bioguard_comparison_winner.zip')) {
 if(-not (Test-Path -LiteralPath (Join-Path $bioRoot $bioFile))) { throw "Missing $bioFile. Ask the project owner for the complete BioGuard source/model files before continuing." }
}
$bioNodeCommand=Get-Command node -ErrorAction SilentlyContinue
$bioNpmCommand=Get-Command npm.cmd -ErrorAction SilentlyContinue
$bioPyCommand=Get-Command py -ErrorAction SilentlyContinue
if(-not $bioNodeCommand -or -not $bioNpmCommand -or -not $bioPyCommand){throw 'Install Node 24 LTS and Python 3.12 (including the Python launcher), then reopen PowerShell.'}
$bioVersion=(& $bioNodeCommand.Source --version).TrimStart('v') -as [version]
if(-not $bioVersion -or $bioVersion.Major -ne 24){throw 'Use Node 24 LTS, then reopen PowerShell.'}
& $bioPyCommand.Source -3.12 -c 'import sys; print("Python",sys.version.split()[0])'
if($LASTEXITCODE -ne 0){throw 'Install Python 3.12 with the Python launcher first.'}
Push-Location -LiteralPath $bioRoot
try {
 $bioPython=Join-Path $bioRoot 'backend/.venv/Scripts/python.exe'
 if(-not (Test-Path -LiteralPath $bioPython)) {
  & $bioPyCommand.Source -3.12 -m venv backend/.venv
  if($LASTEXITCODE -ne 0){throw 'Could not create the backend environment.'}
 }
 & $bioPython -m pip install -r backend/requirements.txt
 if($LASTEXITCODE -ne 0){throw 'Backend dependency installation failed.'}
 & $bioPython backend/setup_model.py
 if($LASTEXITCODE -ne 0){throw 'Model preparation failed. Check the supplied winner ZIP.'}
 Push-Location -LiteralPath (Join-Path $bioRoot 'mobile')
 try { & $bioNpmCommand.Source ci; if($LASTEXITCODE -ne 0){throw 'Mobile dependency installation failed.'} } finally { Pop-Location }
 $bioAccounts=@"
from pathlib import Path
import secrets,sys
sys.path.insert(0,str(Path('backend').resolve()))
from records import Records,password_hash
store=Records(Path('backend/data/private-beta'))
store.initialize(False)
for name,role,display in [('grounds','ground','Ground team'),('ecology','ecology','Ecology field team'),('management','management','Management')]:
    with store.connect() as db:
        existing=db.execute('SELECT id FROM users WHERE username=?',(name,)).fetchone()
    if existing:
        continue
    identifier=store.add_user(name,secrets.token_urlsafe(20),display,role,must_change=False)
    salt=secrets.token_hex(16)
    with store.connect() as db:
        db.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',(salt,password_hash('123',salt),identifier))
print('Local test accounts are ready. Existing users, passwords and reports were preserved.')
"@
 $bioAccounts | & $bioPython -
 if($LASTEXITCODE -ne 0){throw 'Local account preparation failed.'}
 Write-Host 'Ready. Run .\Start-PrivateBeta.ps1 -Mode Web or -Mode Expo.'
 Write-Host 'New local test accounts: grounds / 123, ecology / 123, management / 123.'
} finally { Pop-Location }
