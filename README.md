# BioGuard - get, run and test

**Windows guide.** Only installing the Android APK? Skip to section 4. No source code or laptop setup is needed on the phone.

## 1. Get BioGuard from GitHub

Project: https://github.com/Etticx/BioGuard (ask the owner for access if private).

**First time, with Git:** install Git, open a terminal in the parent folder where you want BioGuard, then run:

```powershell
git clone https://github.com/Etticx/BioGuard.git
cd BioGuard
```

**Already have a Git clone?** Open a terminal inside that BioGuard folder, then update it:

```powershell
git pull --ff-only
```

If Git reports conflicting/local changes, ask the team before changing or deleting files.

**Without Git:** open the GitHub page -> Code -> Download ZIP -> Extract All. Open the extracted project folder (it may be called `BioGuard-main`). A downloaded ZIP cannot use `git pull`; download a fresh ZIP when updating. Keep your old folder/data until the update works.

**Check the download:** the project folder must contain `Start-PrivateBeta.ps1`, `backend/`, `mobile/package.json`, `mobile/src/` and `bioguard_comparison_winner.zip`. If anything is missing, ask the owner for a complete copy.

## 2. Open a terminal and prepare your computer

Open this project folder in VS Code -> Terminal -> New Terminal, and select **PowerShell**. Or open Windows Terminal/PowerShell directly in the project folder. In Command Prompt, type `powershell` first; the launch commands below use PowerShell.

If your terminal is somewhere else, use `cd` with **your actual extracted/cloned folder path**:

```powershell
cd "C:\your-folder\BioGuard"
```

That is an example, not the author's laptop path. Replace it with wherever you saved the project, including `BioGuard-main` if that is its name. You should see `Start-PrivateBeta.ps1` when you run `dir`.

**First-time setup only:** install Node 24 LTS and Python 3.12 (with the Python launcher), reopen your terminal in the project folder, then run:

```powershell
.\Setup-Local.ps1
```

This downloads dependencies, prepares the supplied model, and creates missing local test accounts. Existing accounts, passwords and reports are preserved. After pulling updates, run it again if dependencies changed. Internet access is needed for setup.

If PowerShell blocks scripts, use `Set-ExecutionPolicy -Scope Process Bypass` in that terminal, then retry. This applies only to the current terminal session.

## 3. Run locally: laptop or Expo Go

**Test logins:** `grounds / 123`, `ecology / 123`, `management / 123`. One sign-in opens the correct workspace. These defaults apply to newly created local accounts and the shared APK test server; an existing changed password is preserved.

**Laptop browser:** in the project folder, run:

```powershell
.\Start-PrivateBeta.ps1 -Mode Web
```

Open **http://localhost:8001/**. Keep the terminal open.

**Expo Go on Android or iPhone:** stop Web mode with Ctrl+C, then run:

```powershell
.\Start-PrivateBeta.ps1 -Mode Expo
```

1. Put the phone and laptop on the same Wi-Fi.
2. Open Expo Go compatible with this project's **SDK 57**, and sign in with the same Expo account as the laptop.
3. Scan the QR shown in the terminal: Android uses Expo Go; iPhone uses its Camera app.
4. Sign into BioGuard with a test login above.

If Expo needs login, run these commands in a second terminal in the project folder:

```powershell
cd mobile
npx expo login --browser
cd ..
```

Laptop dashboard remains **http://localhost:8001/**. Expo uses port **8383**. Use one local mode at a time. If port 8001 is busy, open the already-running app or stop its original terminal first.

## 4. Android APK: install and test remotely

[Download BioGuard APK - version 0.2.0, about 101 MB](https://expo.dev/artifacts/eas/cNrNpTOvPanmRZcf_D7iuAk7_yYXG5t2Xn4IsAQCIZc.apk)

Download -> open APK -> allow installation from that browser if asked -> install -> sign in. **No Expo Go or GitHub download is needed for this route.** Use the test logins above.

The current APK connects to the project owner's laptop server. The owner must keep that laptop awake, online and the remote beta running. Cloning the project onto another laptop does not move the existing APK's server.

**Project owner only:** start `./Start-RemoteBeta.ps1` if it is not already running. This requires the prepared model/web export and Cloudflare utility. Stop with Ctrl+C in its terminal or `./Stop-RemoteBeta.ps1`.

**A tunnel restart changes its URL.** The existing APK then needs rebuilding: update `build.preview.env.EXPO_PUBLIC_API_URL` in `mobile/eas.json`, then run from `mobile/`:

```powershell
npx eas-cli@latest build --platform android --profile preview
```

## Keep in mind

- Local browser + Expo share local reports; the shared APK has a separate remote-beta database.
- Keep `backend/data/` when updating: it contains saved reports and photos. GitHub does not include private data or installed dependencies.
- The owner's active remote URL is in `backend/data/remote-beta/active-url.txt`.
- Team introduction: `output/pdf/BioGuard_Team_Introduction.pdf`.

## AI restoration drafts (testing/aiagent)

- Put only your Groq API key in `backend/data/groq-api-key.txt` (ignored by Git), or set backend `GROQ_API_KEY`. Never put it in the mobile app.
- Restart the backend after code updates, then refresh management with Ctrl + F5.
- Confirm the classified species. Correct identification is available if needed. BioGuard downloads selected official botanical profiles itself and caches readable pages for six hours. Then one plain Groq request returns removal, a proposed replacement species, replanting and the handover note together. Groq browser tools are disabled. Edit the draft before Save decision.
- The replacement is a proposal for management approval. Site conditions still need checking. Sources come from the reference pages BioGuard actually retrieved, not invented links. The reference pool covers two herbaceous options and one woody option; these are provisional choices, not an exhaustive search for the best plant. If the response is incomplete or unsupported, BioGuard shows an error without making another request.
- Default model: `openai/gpt-oss-120b`; optional `GROQ_MODEL` must support strict structured outputs. There is no formatter request or automatic Groq retry. If Groq fails and the local backup is configured, BioGuard automatically tries Qwen once.
- Same report revision and confirmed species: reuse the draft for 15 minutes with zero extra Groq requests. A new revision or corrected species is a new draft.
- New attempts: at least 30 seconds apart, maximum 10 per management account per hour and 30 total per hour. Failed attempts count too. Blocked requests use no Groq call. Limits and cache apply to this backend process and reset when it restarts; run one backend worker for this beta.
- Only confirmed species, rough amount and Malaysia region are sent. No photos, precise coordinates, reporter details or report history are sent.
- Groq's own token quotas still apply. The draft shows a usage receipt with the actual number of outgoing Groq requests and the provider request ID when available. Receipts are also saved in the active beta data folder as `ai-usage.jsonl`; they contain no API keys, photos or report text. The active pipeline is `plain-reference-v3` (`/ai/status`, management login required). No live Groq requests are needed to run the offline budget tests.

### Local Qwen backup (optional)

- Groq stays primary. If it fails and a local model is configured, Qwen automatically prepares all four sections with one local request and **zero extra Groq requests**. No backup button is needed. If Qwen also fails, generation stops; Retry draft retries locally.
- Install/start Ollama on the same laptop as the backend. Run `ollama list` to find your installed Qwen model name.
- Put that exact name (for example `qwen3:8b`, only if installed) in `backend/data/ollama-model.txt`, or set `OLLAMA_MODEL` in the terminal before starting BioGuard. Restart the backend and refresh management with Ctrl + F5.
- Ollama must listen on its normal local address `http://127.0.0.1:11434`. No model is downloaded automatically, and its port does not need to be exposed to friends.
- The backup uses the same botanical reference checks and editable sections. Internet is still needed for uncached reference pages. Speed and quality depend on the installed model and laptop; management must review the result.
- Groq and local drafts have separate 15-minute caches and per-account cooldowns, so a Groq quota error does not delay the first local attempt. The shared hourly cap and in-flight protection still apply. Usage receipts record Groq and local request counts separately.

## Elmina live map

- New reports require **Pin plant location** on the OpenStreetMap map near Elmina Lakeside Mall. Drag the map beneath the red pin, scroll/pinch to zoom, then tap **Done**. No device GPS permission is requested.
- The approximate pilot rectangle is 3.17790–3.18343 latitude and 101.50485–101.51333 longitude. Centre: 3.180661, 101.509091. It is a prototype boundary, not a surveyed SDP property boundary.
- Reports save real latitude/longitude with map version `elmina-lakeside-v1`. The server rejects new live-map reports outside the boundary. Management shows the same map and saved point.
- Internet and a reachable backend are required. Map tiles load directly from OpenStreetMap with visible attribution and normal browser caching; no offline tile downloads or background prefetch are provided. Leaflet 1.9.4 is bundled locally under `web/vendor/leaflet/` with its licence.
- Older image-map reports remain readable on their original illustration. An old draft must be pinned again before sending from the updated app; no coordinates are guessed from the picture.
- Restart `./Start-PrivateBeta.ps1 -Mode Web` after this update, then refresh the browser. The browser export has also been rebuilt. Expo Go users reload the project after restarting its backend; installed APKs need a new build.
- The shared map route is `/maps/elmina`; other application pages retain their existing frame restrictions. No spread prediction or automatic identification of drains is included.

Management location maps now highlight the report's prototype inspection block (B01–B20). A shared boundary shows both IDs; mapped water shows its name instead of selecting a land block. Orange shading identifies the location block, not predicted spread or confirmed infestation. Block data comes from `web/elmina-inspection-blocks.geojson`; it uses OSM features with merged fragments and artificial subdivisions, not official SDP boundaries. Grounds pinning and AI generation are unchanged. Refresh the management page to load the overlay; no Expo rebuild is required for these backend-served map assets.
