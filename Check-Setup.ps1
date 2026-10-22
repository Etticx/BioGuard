# Read-only checks for the documented Windows setup. Does not create/reset accounts.
$ErrorActionPreference='Stop'
$bioRoot=$PSScriptRoot
$bioFailures=0
function Show-BioCheck([string]$Name,[bool]$Passed,[string]$Detail) {
 if($Passed){Write-Host "[OK] $Name - $Detail"}else{Write-Host "[MISSING] $Name - $Detail"; $script:bioFailures++}
}
$bioNode=Get-Command node -ErrorAction SilentlyContinue
if($bioNode){
 $bioVersion=(& $bioNode.Source --version).TrimStart('v') -as [version]
 Show-BioCheck 'Node.js' ($null -ne $bioVersion -and $bioVersion.Major -eq 24 -and $bioVersion -ge [version]'24.3.0') "Found $bioVersion; setup expects Node 24 LTS."
}else{Show-BioCheck 'Node.js' $false 'Install Node 24 LTS and reopen PowerShell.'}
foreach($bioFile in @('backend/requirements.txt','backend/completion_pdf.py','backend/inspection_rules.json','web/elmina-inspection-blocks.geojson','web/elmina-map-config.json','mobile/package-lock.json','bioguard_comparison_winner.zip')){
 Show-BioCheck $bioFile (Test-Path -LiteralPath (Join-Path $bioRoot $bioFile)) 'Required project file.'
}
$bioPython=Join-Path $bioRoot 'backend/.venv/Scripts/python.exe'
if(Test-Path -LiteralPath $bioPython){
 $bioCheck=@'
import sys,json,importlib.metadata
from pathlib import Path
root=Path(sys.argv[1])
assert sys.version_info[:2]==(3,12),'Recreate the environment using Python 3.12.'
assert Path(sys.prefix).resolve()==(root/'backend/.venv').resolve(),'Use this checkout\'s environment, not a copied environment.'
for package in ['tensorflow','keras','numpy','pillow','fastapi','uvicorn','python-multipart','reportlab']:
    print(package+': '+importlib.metadata.version(package))
required=['bioguard.keras','class_names.json','preprocessing.json','selection.json','species_policy.json']
for name in required:assert (root/'backend/model'/name).is_file(),'Missing installed model file: '+name
classes=json.loads((root/'backend/model/class_names.json').read_text(encoding='utf-8'))
assert len(classes)==9,'Expected nine supported species.'
sys.path.insert(0,str(root/'backend'))
import app
print('Backend imports, inspection resources and installed model files: OK')
'@
 $bioCheck | & $bioPython - $bioRoot
 Show-BioCheck 'Backend environment' ($LASTEXITCODE -eq 0) 'Dependencies, resource imports and model files; live inference is checked by /health after startup.'
}else{Show-BioCheck 'Backend environment' $false 'Run .\Setup-Local.ps1 first.'}
Show-BioCheck 'Mobile dependencies' (Test-Path -LiteralPath (Join-Path $bioRoot 'mobile/node_modules/expo/bin/cli')) 'Run setup if missing; do not copy node_modules from another computer.'
Write-Host 'Optional Groq/Ollama configuration is private and is not printed by this check.'
if($bioFailures){throw "$bioFailures setup check(s) need attention. Follow README.md."}
Write-Host 'Setup checks passed. Start the app, then verify identification_available at /health.'
