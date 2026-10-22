# Fresh-copy setup verification

Verified on 22 October 2026 using a separate local Git clone on the current Windows x64 computer. This was not a test on a second physical computer. No original reports, accounts, keys, virtual environment, node_modules or installed-model directory were copied into that clone. Download caches on the computer were available.

## Passed

- Documented setup in Windows PowerShell 5.1 with Python 3.12.6 and Node 24.19.0; dependencies installed from the manifests/lockfile.
- A second setup run and Check-Setup.ps1.
- Python dependency compatibility check (`pip check`).
- Supplied model ZIP installation; actual EfficientNetV2B0 load and inference on a licensed reference photo.
- Start-PrivateBeta.ps1 Web build and server startup on a separate test port.
- Browser login page render and authenticated API logins for Grounds, Management and Ecology.
- Synthetic report with a real map pin, deterministic sourced inspection guidance, management assignment, delivery of the saved brief/map point to Ecology, inspection submission and management review.
- TypeScript check and Expo lint using the clean installation.
- Docker resource regression: failed with the old COPY inputs (missing inspection_rules.json), then passed with the corrected inputs.
- PowerShell syntax checks and git diff whitespace check.

No Groq or Ollama requests were needed or made by the smoke test.

## Fixes made

1. Replace a Python `-c` version probe whose quoting failed under Windows PowerShell 5.1.
2. Invoke npm with the checked Node executable; an npm.cmd from a different installation could otherwise use an unsupported Node version.
3. Include required backend JSON files in Docker packaging.
4. Check inspection map/rule resources before setup and provide a read-only setup checker.

## Not established by this test

- Physical Android/iPhone, fresh APK, macOS, Linux or Windows ARM operation.
- Full Docker image build/run: the Docker engine was unavailable. Only packaging-resource import behaviour was tested.
- Another network's firewall/VPN/guest Wi-Fi behaviour.
- Provider credentials/quota or the availability/quality of a new computer's local Ollama model.
- Field identification accuracy or ecological treatment effectiveness.

Dependency installation printed existing npm audit advisories. This setup work did not perform broad dependency upgrades or establish production security readiness. Use the documented private/local demo route.

The main README gives the supported Windows quick start and separates optional AI/phone/hosting setup. These changes must be committed and pushed before another computer receives them through GitHub.
