# BioGuard

BioGuard connects plant identification, map-based reporting, management approval and ecology inspection/restoration work. The prototype supports nine selected plant species. Inspection blocks organise work; they do not predict spread.

## Quick start on another Windows computer

Use **Windows 10/11, 64-bit x86**, **Python 3.12**, **Node.js 24 LTS**, and **Git**. Install Python with the Python launcher. Internet is needed to install dependencies, load map tiles and use cloud AI. An Android phone, Android Studio, Docker and a Groq key are **not required** to try the browser app.

Official downloads: [Git](https://git-scm.com/downloads), [Python](https://www.python.org/downloads/windows/), [Node.js](https://nodejs.org/en/download).

Open a **PowerShell** terminal. Run the following commands one at a time.

### 1. Download the project — first time only

```powershell
git clone https://github.com/Etticx/BioGuard.git
cd BioGuard
```

If GitHub asks you to sign in, use an account with repository access. Run the remaining commands inside this folder: `dir` should show `Setup-Local.ps1`, `Start-PrivateBeta.ps1`, `backend`, `mobile`, and `bioguard_comparison_winner.zip`.

The trained model archive is included. **No model training, original dataset download or author-specific folder path is needed.** GitHub's Download ZIP also works, but that folder cannot use `git pull`.

### 2. Check the installed tools

```powershell
git --version
node --version
py -3.12 --version
```

Node should report `v24...`; Python should report `Python 3.12...`. Reopen your terminal after installing them. Use the 64-bit x86 Python installer, not ARM Python, for this documented Windows route.

### 3. Prepare dependencies and local accounts

```powershell
.\Setup-Local.ps1
```

This installs the Python and mobile dependencies, extracts the supplied model, and creates missing local demo accounts. It preserves existing accounts, passwords and reports. The first run can take several minutes and download substantial dependencies, including TensorFlow. Wait for the `Ready` message.

If PowerShell refuses to run the script, you can invoke just that script with a process-specific policy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-Local.ps1
```

This does not change your permanent execution policy. Review the repository scripts before running them; do not bypass organisational IT policy.

Optional setup check:

```powershell
.\Check-Setup.ps1
```

### 4. Start BioGuard

```powershell
.\Start-PrivateBeta.ps1 -Mode Web
```

The script builds the browser app and starts its backend. Keep the terminal open. Once startup finishes, open:

**http://localhost:8001/**

New local demo accounts:

| Username | Password | Workspace |
| --- | --- | --- |
| `grounds` | `123` | Identify and report plants |
| `management` | `123` | Review reports, instructions and work |
| `ecology` | `123` | Inspect assigned locations and submit evidence |

These passwords are for local/private testing. An existing password is not reset by setup. Do not expose this demo server or these accounts to the public Internet.

Stop the server with **Ctrl+C** in its terminal.

### 5. Confirm it works

Open **http://localhost:8001/health**. Successful model startup reports:

```json
{
  "status": "ready",
  "identification_available": true,
  "supported_species_count": 9
}
```

The response contains additional fields. `status: ready` alone does not prove the model loaded: check `identification_available` too. Then sign in as Grounds, identify a plant photo, pin its location and submit a demo report. Management and Ecology use the same server/database.

## Get updates — when you already have the project

Stop BioGuard with Ctrl+C, open PowerShell **inside your existing BioGuard folder**, then run:

```powershell
git status
git switch main
git pull --ff-only origin main
.\Setup-Local.ps1
.\Start-PrivateBeta.ps1 -Mode Web
```

`clone` downloads the project the first time; `pull` updates an existing Git copy. Setup is safe to rerun after an update and preserves existing records. Start rebuilds the browser app so current code appears. Refresh the browser with **Ctrl+F5**.

If `git status` shows your own changes, or `switch`/`pull` fails, **stop and resolve that with the team**. Do not use `reset --hard`, delete your folder, or overwrite your work just to update.

Only committed and pushed work is available to other computers. Changes sitting on someone else's laptop are not downloaded by `git pull`.

## Optional AI setup

The app and trained plant classifier run without a Groq account. **Automatic removal/replanting drafting requires configured AI.** Management can enter instructions manually without it. Inspection guidance can use a source-based template if model generation is unavailable.

### Groq — primary drafting provider

On the backend computer, create this file in a text editor:

```text
backend/data/groq-api-key.txt
```

Put **only your Groq API key** in it. This folder is ignored by Git. Restart BioGuard afterward. Never place keys in screenshots, the README, Expo public environment variables or GitHub.

Alternatively, set `GROQ_API_KEY` in the PowerShell session that starts BioGuard. Default model: `openai/gpt-oss-120b`; optional `GROQ_MODEL` must support the required structured output.

### Local Qwen through Ollama — optional backup

Install Ollama separately on the **backend computer** and install a suitable Qwen model. Run:

```powershell
ollama list
```

Create `backend/data/ollama-model.txt` containing the exact installed model name from that list, then restart BioGuard. Alternatively set `OLLAMA_MODEL` in the launch session. Ollama must be reachable at `http://127.0.0.1:11434`.

**A folder containing model files is not enough.** This backup calls Ollama; it does not automatically load another computer's Qwen folder or install/download a model. Hardware, memory requirements and speed depend on the model you choose. You can skip this entirely for the basic demo.

Groq stays primary. Each drafting task makes at most one Groq attempt and, when configured, one local backup attempt. Inspection and restoration are **separate tasks**, so opening an inspection report and later generating a restoration plan can make two requests total. Cached unchanged drafts make no new request. All instructions require review.

## Try it on a phone

### Simplest: phone browser

Keep Web mode running. Put the phone and laptop on the same private Wi-Fi and open the **Phone browser** address printed in the terminal, for example `http://192.168.1.20:8001/`.

`localhost` on a phone means the phone itself, not your laptop. Map tiles need Internet access. Use a photo from the gallery if camera capture is unavailable over local HTTP. If Windows asks for firewall access, use a trusted private network; do not disable the firewall or expose the port publicly.

### Expo Go

Stop Web mode, then run:

```powershell
.\Start-PrivateBeta.ps1 -Mode Expo
```

Use an Expo Go version compatible with **SDK 57**, keep both devices on the same private Wi-Fi, and scan the terminal's QR code. Expo uses port 8383 by default; the backend uses 8001. Follow any Expo account/sign-in requirements shown by your installed Expo Go version. To sign in from the project:

```powershell
cd mobile
npx expo login --browser
cd ..
```

### Existing Android APK

An installed APK has a backend address embedded at build time. **Cloning BioGuard onto a new laptop does not redirect an old APK to that laptop.** Use the browser/Expo route first. A standalone APK needs a reachable HTTPS backend and a new build configured for it. See [advanced running notes](docs/RUNNING_AND_AI.md).

## Where records and settings live

- Local demo accounts, reports and photos: `backend/data/private-beta/`.
- Groq key: `backend/data/groq-api-key.txt` (optional, private).
- Ollama model name: `backend/data/ollama-model.txt` (optional, private).
- Installed model: `backend/model/`, extracted from the tracked ZIP.
- Browser build: `mobile/.beta-dist/`, regenerated at startup.
- Inspection rules: `backend/inspection_rules.json`.
- Inspection map boundaries: `web/elmina-inspection-blocks.geojson`.

GitHub does **not** transfer accounts, private reports, keys, installed dependencies or the local Ollama model. Each new setup starts with its own local demo data. To transfer real records, stop the original server and handle a separate private backup/restore with the owner. Do not commit the database to GitHub.

## Common problems

- **Missing model ZIP or folders:** check you downloaded the full repository. The ZIP must be `bioguard_comparison_winner.zip` in the project root; a Git LFS pointer is not a usable model ZIP.
- **Node version rejected:** install Node 24 LTS, reopen PowerShell and check `node --version`. Do not copy `node_modules` from another computer.
- **Python not found:** install Python 3.12 with its launcher; check `py -3.12 --version`.
- **Copied Python environment does not run:** virtual environments are machine-specific. Use a fresh clone and rerun setup; do not share `backend/.venv` between machines.
- **Dependency installation fails:** read the first error; check Internet/proxy access, supported Python/Windows architecture and free disk space. Do not silently skip failed installation steps.
- **Port 8001 is in use:** stop the original server or choose another port: `.\Start-PrivateBeta.ps1 -Mode Web -ApiPort 8002`, then open `http://localhost:8002/`.
- **Page does not load:** keep the server terminal open and wait for startup; inspect the error in that terminal.
- **App loads but identification is unavailable:** check `/health`, rerun setup, and inspect the backend startup error. Do not claim successful model setup from the login page alone.
- **Phone cannot connect:** check the current printed LAN address, same Wi-Fi, guest-network isolation and private-network firewall permission. VPNs can select the wrong network adapter.
- **AI unavailable/rate-limited:** check your own configuration and provider quota. The plant classifier is separate from Groq. Manual instructions remain available.
- **Old screen after an update:** stop/restart the launcher and refresh with Ctrl+F5. Expo Go needs a reload; an installed APK needs rebuilding.

## Developer checks

From the project root after setup:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..
node --test web/tests/*.test.cjs
cd mobile
npm test
npm run typecheck
npm run lint
cd ..
```

Tests use synthetic fixtures. They do not replace a field trial, a physical phone test or an independently verified ecological assessment.

## Other operating systems and hosting

The quick-start scripts above are **Windows PowerShell scripts**. Do not paste them into a macOS/Linux shell. The repository also includes Docker and HTTPS deployment configuration for a separate hosting workflow; these require additional account, storage and security configuration. Local browser success is not proof that a public deployment or an existing APK works.

See [running and feature notes](docs/RUNNING_AND_AI.md) for mapping, inspection, AI budgets and APK details. This is a private prototype; no public deployment is performed by local setup.

## Final demo release and Android APK

The prepared source version is **1.0.0**. See [the final release guide](docs/FINAL_RELEASE.md) for the separate APK build, backend address, version tracking and physical-phone checks. Pulling this repo does not update an APK already installed on a phone. The older 0.2.0 APK is not the final build.
